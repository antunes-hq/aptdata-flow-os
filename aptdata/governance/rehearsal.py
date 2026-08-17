"""Deterministic read-only rehearsal of the trusted squad lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from aptdata.governance.gates import check_integration, check_ready_for_judging
from aptdata.governance.judge import GovernanceJudge
from aptdata.governance.models import (
    AcceptanceCriterion,
    Assignment,
    ContextPacket,
    EvidenceKind,
    EvidenceRecord,
    EvidenceResult,
    EvidenceSource,
    MaestroAction,
    MaestroDecision,
    PacketState,
    Risk,
    SourceRef,
    SquadDefinition,
    SquadRole,
    WorkPacket,
)
from aptdata.governance.store import GovernanceStore


def run_read_only_rehearsal(path: str | Path = ":memory:") -> dict[str, Any]:
    """Run a deterministic end-to-end governance rehearsal.

    No model, network, repository, deployment or user data is touched. The
    role outputs are intentionally synthetic; the rehearsal proves lifecycle,
    evidence, independent judgement, human approval and durable recovery.
    """
    now = datetime.now(timezone.utc)
    context = ContextPacket(
        id="cp_rehearsal_001",
        source=SourceRef(
            actor="user", channel="rehearsal", reference="fixture://my-universe"
        ),
        intent="Validar o ciclo confiável antes do desenvolvimento",
        why="Provar rastreabilidade sem tocar produção",
        domain="personal",
        desired_experience="baixo ruído e controle humano",
        unknowns=["qual UX final do onboarding"],
    )
    squad = SquadDefinition(
        id="squad_rehearsal_001",
        name="Trusted squad rehearsal",
        roles=[
            SquadRole(id="po", capability="product_context"),
            SquadRole(id="tech_lead", capability="architecture"),
            SquadRole(id="ui_ux", capability="human_experience"),
            SquadRole(id="qa", capability="verification"),
            SquadRole(id="executor", capability="read_only_execution"),
            SquadRole(id="judge", capability="independent_judgement"),
        ],
        executor_policy={"allowed": ["rehearsal"], "fallback": "explicit_only"},
    )
    packet = WorkPacket(
        id="wp_rehearsal_001",
        context_packet_id=context.id,
        squad_definition_id=squad.id,
        objective="Provar registro e julgamento de um slice read-only",
        scope_in=["contratos de governança", "store SQLite temporário"],
        scope_out=["produção", "My Universe real", "LLM", "deploy"],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-REHEARSAL-001",
                description="Todos os registros podem ser recuperados depois",
                verification="GovernanceStore reabre o SQLite e recupera o WorkPacket",
            ),
            AcceptanceCriterion(
                id="AC-REHEARSAL-002",
                description="Judge é independente do executor",
                verification="JudgeResult.independence_check.independent is True",
            ),
        ],
        risk=Risk(
            level="low",
            hazards=["ensaio sintético não prova comportamento de produção"],
            rollback="apagar o SQLite temporário do ensaio",
        ),
        assignments=[
            Assignment(role=role, agent_id=f"rehearsal_{role}", accepted_at=now)
            for role in ("po", "tech_lead", "ui_ux", "qa", "executor", "judge")
        ],
    )
    packet.transition(PacketState.READY).transition(PacketState.RUNNING)

    evidence = [
        EvidenceRecord(
            id=f"ev_rehearsal_{role}",
            work_packet_id=packet.id,
            kind=EvidenceKind.REVIEW if role != "qa" else EvidenceKind.TEST,
            claim=f"{role} output foi produzido dentro do escopo read-only",
            command="python -m aptdata.governance.rehearsal",
            output_digest=f"sha256:rehearsal-{role}",
            result=EvidenceResult.PASS,
            source=EvidenceSource(
                path="aptdata/governance/rehearsal.py", revision="working-tree"
            ),
            captured_at=now,
            captured_by=f"rehearsal_{role}",
            limitations=["ensaio sintético; não é prova de runtime externo"],
        )
        for role in ("po", "tech_lead", "ui_ux", "qa", "executor")
    ]
    ready_report = check_ready_for_judging(packet, squad, evidence)
    if not ready_report.passed:
        raise RuntimeError(f"rehearsal failed before judging: {ready_report.codes}")
    packet.transition(PacketState.JUDGING)

    judge = GovernanceJudge("rehearsal_judge").judge(
        packet,
        squad,
        evidence,
        created_at=now,
    )
    packet.transition(PacketState.APPROVED)
    maestro = MaestroDecision(
        id="md_rehearsal_001",
        work_packet_id=packet.id,
        judge_result_id=judge.id,
        action=MaestroAction.APPROVE,
        rationale="Aprovo somente o ensaio read-only; não autoriza produção.",
        actor="maestro_fixture",
        created_at=now,
    )
    integration_report = check_integration(packet, judge, maestro)
    if not integration_report.passed:
        raise RuntimeError(
            f"rehearsal failed before integration: {integration_report.codes}"
        )
    packet.transition(PacketState.INTEGRATED)

    temporary_path: str | None = None
    store_path: str | Path = path
    temp_file = None
    if str(path) == ":memory:":
        temp_file = NamedTemporaryFile(suffix=".db", delete=False)
        temporary_path = temp_file.name
        temp_file.close()
        store_path = temporary_path
    try:
        with GovernanceStore(store_path) as store:
            store.append_many([context, squad, packet, *evidence, judge, maestro])
            persisted_count = store.count()
        with GovernanceStore(store_path) as reopened:
            recovered = reopened.get(WorkPacket, packet.id)
            recovered_records = reopened.for_work_packet(packet.id)
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
        if temp_file is not None:
            Path(f"{temporary_path}-wal").unlink(missing_ok=True)
            Path(f"{temporary_path}-shm").unlink(missing_ok=True)

    if recovered is None or recovered.state is not PacketState.INTEGRATED:
        raise RuntimeError("rehearsal recovery did not return integrated WorkPacket")

    return {
        "work_packet_id": packet.id,
        "state": packet.state.value,
        "ready_gate": ready_report.passed,
        "judge_verdict": judge.verdict.value,
        "judge_independent": judge.independence_check.independent,
        "maestro_action": maestro.action.value,
        "integration_gate": integration_report.passed,
        "persisted_records": persisted_count,
        "recovered_records_for_packet": len(recovered_records),
        "scope_out": packet.scope_out,
    }


__all__ = ["run_read_only_rehearsal"]
