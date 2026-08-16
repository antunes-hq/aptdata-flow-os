"""Confidence gate tests for trusted squad governance."""

from datetime import datetime, timezone

from aptdata.governance import (
    AcceptanceCriterion,
    EvidenceKind,
    EvidenceRecord,
    EvidenceResult,
    EvidenceSource,
    IndependenceCheck,
    JudgeCheck,
    JudgeResult,
    MaestroAction,
    MaestroDecision,
    PacketState,
    Risk,
    SquadDefinition,
    SquadRole,
    Verdict,
    WorkPacket,
    check_integration,
    check_ready_for_judging,
)

NOW = datetime.now(timezone.utc)


def squad() -> SquadDefinition:
    return SquadDefinition(
        id="squad_gate",
        name="gate",
        roles=[
            SquadRole(id="executor", capability="execute"),
            SquadRole(id="judge", capability="judge"),
        ],
        executor_policy={"allowed": ["hermes"]},
    )


def packet() -> WorkPacket:
    return WorkPacket(
        id="wp_gate",
        context_packet_id="cp_gate",
        squad_definition_id="squad_gate",
        objective="test gate",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1", description="pass", verification="pytest"
            )
        ],
        risk=Risk(level="low", rollback="remove fixture"),
        assignments=[
            {
                "role": "executor",
                "agent_id": "coder",
                "accepted_at": NOW,
            },
            {
                "role": "judge",
                "agent_id": "reviewer",
                "accepted_at": NOW,
            },
        ],
        state=PacketState.RUNNING,
    )


def evidence(result=EvidenceResult.PASS) -> EvidenceRecord:
    return EvidenceRecord(
        id="ev_gate",
        work_packet_id="wp_gate",
        kind=EvidenceKind.TEST,
        claim="focused tests pass",
        command="pytest -q",
        output_digest="sha256:gate",
        result=result,
        source=EvidenceSource(path="tests/test_governance_gates.py", revision="abc"),
        captured_at=NOW,
        captured_by="qa",
    )


def judge() -> JudgeResult:
    return JudgeResult(
        id="jr_gate",
        work_packet_id="wp_gate",
        judge_agent_id="reviewer",
        independence_check=IndependenceCheck(
            executor_agent_id="coder", independent=True, reason="different agents"
        ),
        checks=[JudgeCheck(id="J-1", subject="scope", result=EvidenceResult.PASS)],
        verdict=Verdict.GO,
        created_at=NOW,
    )


def maestro() -> MaestroDecision:
    return MaestroDecision(
        id="md_gate",
        work_packet_id="wp_gate",
        judge_result_id="jr_gate",
        action=MaestroAction.APPROVE,
        rationale="approved after evidence",
        actor="lucas",
        created_at=NOW,
    )


def test_ready_gate_passes_only_with_assignments_and_evidence() -> None:
    report = check_ready_for_judging(packet(), squad(), [evidence()])
    assert report.passed
    assert report.codes == []


def test_ready_gate_rejects_missing_assignment() -> None:
    work = packet()
    work.assignments = [work.assignments[0]]
    report = check_ready_for_judging(work, squad(), [evidence()])
    assert not report.passed
    assert "SQUAD-001" in report.codes


def test_ready_gate_rejects_missing_or_inconclusive_evidence() -> None:
    assert "EVID-005" in check_ready_for_judging(packet(), squad(), []).codes
    report = check_ready_for_judging(
        packet(), squad(), [evidence(EvidenceResult.INCONCLUSIVE)]
    )
    assert "EVID-002" in report.codes


def test_integration_requires_maestro_decision() -> None:
    work = packet()
    work.state = PacketState.APPROVED
    report = check_integration(work, judge(), None)
    assert not report.passed
    assert "MAESTRO-001" in report.codes


def test_integration_passes_with_judge_and_maestro() -> None:
    work = packet()
    work.state = PacketState.APPROVED
    report = check_integration(work, judge(), maestro())
    assert report.passed


def test_integration_rejects_no_go() -> None:
    work = packet()
    work.state = PacketState.APPROVED
    rejected = judge().model_copy(
        update={
            "verdict": Verdict.NO_GO,
            "findings": [
                {
                    "severity": "critical",
                    "kind": "missing_evidence",
                    "statement": "missing",
                }
            ],
        }
    )
    report = check_integration(work, rejected, maestro())
    assert not report.passed
    assert "JUDGE-002" in report.codes


def test_integration_rejects_unapproved_packet() -> None:
    report = check_integration(packet(), judge(), maestro())
    assert not report.passed
    assert "PACKET-002" in report.codes
