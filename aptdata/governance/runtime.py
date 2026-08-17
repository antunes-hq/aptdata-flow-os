"""Read-only governance hooks for real workflow executions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aptdata.events.models import FlowEvent
from aptdata.governance.models import (
    ContextPacket,
    EvidenceKind,
    EvidenceRecord,
    EvidenceResult,
    EvidenceSource,
    PacketState,
    SquadDefinition,
    WorkPacket,
)
from aptdata.governance.store import GovernanceStore


class GovernanceWorkflowBinding:
    """Attach durable governance records to an existing workflow run.

    This binding records lifecycle and evidence only. It never dispatches an
    agent, calls a provider, changes a repository or decides a verdict.
    """

    def __init__(
        self,
        *,
        context: ContextPacket,
        squad: SquadDefinition,
        packet: WorkPacket,
        store: GovernanceStore,
        executor_agent_id: str,
        source_revision: str = "working-tree",
        workspace_id: str = "local",
        project_id: str = "aptdata-flow-os",
    ) -> None:
        self.context = context
        self.squad = squad
        self.packet = packet
        self.store = store
        self.executor_agent_id = executor_agent_id
        self.source_revision = source_revision
        self.workspace_id = workspace_id
        self.project_id = project_id
        self._runs: dict[str, str] = {}
        self.last_run_id: str | None = None

    def run_flow(
        self,
        flow: Any,
        inputs: list[Any],
        *,
        flow_name: str | None = None,
    ) -> list[Any]:
        """Run an existing BaseFlow with durable governance correlation."""
        run_id = f"{flow_name or getattr(flow, 'flow_id', 'flow')}_{uuid4().hex}"
        self.start(run_id)
        self.last_run_id = run_id
        try:
            result = flow.run(inputs)
        except Exception as exc:
            self.finish(
                run_id,
                workflow_name=flow_name or getattr(flow, "flow_id", "flow"),
                success=False,
                result={"error_type": type(exc).__name__},
            )
            raise
        self.finish(
            run_id,
            workflow_name=flow_name or getattr(flow, "flow_id", "flow"),
            success=True,
            result=result,
        )
        return result

    def start(self, run_id: str) -> WorkPacket:
        """Persist context/squad and a running packet; reject unsafe setup."""
        if self.packet.state is not PacketState.READY:
            raise ValueError(
                f"governed workflow requires ready packet: {self.packet.state}"
            )
        required = {role.id for role in self.squad.roles if role.required}
        assigned = {assignment.role for assignment in self.packet.assignments}
        missing = sorted(required - assigned)
        if missing:
            raise ValueError(f"governed workflow missing assignments: {missing}")
        executor = next(
            (
                assignment.agent_id
                for assignment in self.packet.assignments
                if assignment.role == "executor"
            ),
            None,
        )
        if executor != self.executor_agent_id:
            raise ValueError("binding executor does not match WorkPacket assignment")

        self._append_if_absent(self.context)
        self._append_if_absent(self.squad)
        self._append_if_absent(self.packet)
        running = self.packet.model_copy(
            update={"version": self.packet.version + 1, "state": PacketState.RUNNING}
        )
        self.store.append(running)
        self.store.append_event(
            self._event(
                event_type="workflow.started",
                run_id=run_id,
                severity="info",
                summary=f"Workflow run {run_id} started",
            )
        )
        self._runs[run_id] = self.packet.id
        return running

    def finish(
        self,
        run_id: str,
        *,
        workflow_name: str,
        success: bool,
        result: Any = None,
    ) -> EvidenceRecord:
        """Persist sanitized runtime evidence and a judging-ready packet."""
        packet_id = self._runs.get(run_id)
        if packet_id != self.packet.id:
            raise ValueError(f"unknown governed run: {run_id}")
        captured_at = datetime.now(timezone.utc)
        summary = self._safe_summary(result)
        digest = hashlib.sha256(
            json.dumps(summary, sort_keys=True).encode("utf-8")
        ).hexdigest()
        evidence = EvidenceRecord(
            id=f"ev_{packet_id}_{run_id}",
            work_packet_id=packet_id,
            kind=EvidenceKind.RUNTIME,
            claim=f"Workflow {workflow_name} completed with success={success}",
            command=f"workflow:{workflow_name}.execute",
            output_digest=f"sha256:{digest}",
            result=EvidenceResult.PASS if success else EvidenceResult.FAIL,
            source=EvidenceSource(
                path=f"workflow:{workflow_name}", revision=self.source_revision
            ),
            captured_at=captured_at,
            captured_by=self.executor_agent_id,
            limitations=["runtime hook records summary only; Judge is separate"],
        )
        self.store.append(evidence)
        judging = self.packet.model_copy(
            update={
                "version": self.packet.version + 2,
                "state": PacketState.JUDGING,
                "evidence_refs": [*self.packet.evidence_refs, evidence.id],
            }
        )
        self.store.append(judging)
        self.store.append_event(
            self._event(
                event_type=("workflow.completed" if success else "workflow.failed"),
                run_id=run_id,
                severity="info" if success else "error",
                summary=(
                    f"Workflow {workflow_name} completed"
                    if success
                    else f"Workflow {workflow_name} failed"
                ),
                evidence_refs=[evidence.id],
                metadata={"work_packet_id": packet_id},
            )
        )
        return evidence

    def _event(
        self,
        *,
        event_type: str,
        run_id: str,
        severity: str,
        summary: str,
        evidence_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FlowEvent:
        return FlowEvent(
            event_id=uuid4(),
            schema_version=1,
            event_type=event_type,
            workspace_id=self.workspace_id,
            project_id=self.project_id,
            run_id=run_id,
            severity=severity,
            human_summary=summary,
            flow_definition_id=self.squad.id,
            evidence_refs=evidence_refs,
            metadata=metadata,
        )

    def _append_if_absent(self, record: Any) -> None:
        record_type = type(record)
        record_id = record.id
        if self.store.get(record_type, record_id) is None:
            self.store.append(record)

    @staticmethod
    def _safe_summary(result: Any) -> dict[str, Any]:
        """Return metadata only; never persist workflow payloads or secrets."""
        if result is None:
            return {"result_type": "none"}
        if isinstance(result, (list, tuple, set, dict)):
            return {"result_type": type(result).__name__, "items": len(result)}
        return {"result_type": type(result).__name__}


__all__ = ["GovernanceWorkflowBinding"]
