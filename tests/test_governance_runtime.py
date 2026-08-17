"""Tests for automatic governance records around real Workflow.execute calls."""

import json
from datetime import datetime, timezone

import pytest

from aptdata.core.workflow import Workflow
from aptdata.governance import (
    AcceptanceCriterion,
    Assignment,
    ContextPacket,
    EvidenceRecord,
    EvidenceResult,
    GovernanceJudge,
    GovernanceStore,
    GovernanceWorkflowBinding,
    Risk,
    SourceRef,
    SquadDefinition,
    SquadRole,
    WorkPacket,
)

NOW = datetime.now(timezone.utc)


def setup_governance(store: GovernanceStore) -> GovernanceWorkflowBinding:
    context = ContextPacket(
        id="cp_runtime",
        source=SourceRef(actor="user", channel="test", reference="runtime-fixture"),
        intent="testar hook de execução",
        why="registrar sem perder evidência",
        domain="development",
    )
    squad = SquadDefinition(
        id="squad_runtime",
        name="runtime",
        roles=[
            SquadRole(id="executor", capability="execute"),
            SquadRole(id="judge", capability="judge"),
        ],
        executor_policy={"allowed": ["test"]},
    )
    packet = WorkPacket(
        id="wp_runtime",
        context_packet_id=context.id,
        squad_definition_id=squad.id,
        objective="executar workflow registrado",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-RUNTIME",
                description="runtime evidencia",
                verification="pytest",
            )
        ],
        risk=Risk(level="low", rollback="apagar o fixture"),
        assignments=[
            Assignment(role="executor", agent_id="executor_test", accepted_at=NOW),
            Assignment(role="judge", agent_id="judge_test", accepted_at=NOW),
        ],
        state="ready",
    )
    return GovernanceWorkflowBinding(
        context=context,
        squad=squad,
        packet=packet,
        store=store,
        executor_agent_id="executor_test",
    )


def test_workflow_success_records_runtime_evidence(tmp_path) -> None:
    with GovernanceStore(tmp_path / "runtime.db") as store:
        binding = setup_governance(store)
        workflow = Workflow("runtime_success", governance_binding=binding)
        workflow.add_step(lambda data: [*data, "ok"])

        assert workflow.execute(["input"]) == ["input", "ok"]
        packet = store.get(WorkPacket, "wp_runtime")
        rows = store.for_work_packet("wp_runtime")
        evidence = EvidenceRecord.model_validate(json.loads(rows[0]["payload"]))

        assert evidence.result is EvidenceResult.PASS
        assert evidence.kind.value == "runtime"
        assert packet is not None
        assert packet.state.value == "judging"
        assert store.count() == 6

        judge = GovernanceJudge("judge_test").judge(
            packet,
            store.get(SquadDefinition, "squad_runtime"),
            [evidence],
        )
        assert judge.verdict.value == "go"


def test_workflow_failure_records_fail_and_reraises(tmp_path) -> None:
    with GovernanceStore(tmp_path / "runtime.db") as store:
        binding = setup_governance(store)
        workflow = Workflow("runtime_failure", governance_binding=binding)

        def explode(_data):
            raise RuntimeError("synthetic failure")

        workflow.add_step(explode)
        with pytest.raises(RuntimeError, match="synthetic failure"):
            workflow.execute(["input"])

        rows = store.for_work_packet("wp_runtime")
        evidence = EvidenceRecord.model_validate(json.loads(rows[0]["payload"]))
        assert evidence.result is EvidenceResult.FAIL
        assert evidence.output_digest.startswith("sha256:")

def test_workflow_without_binding_keeps_existing_behavior() -> None:
    workflow = Workflow("plain")
    workflow.add_step(lambda data: data + 1)
    assert workflow.execute(1) == 2
