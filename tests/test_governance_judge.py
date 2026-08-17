"""Tests for the deterministic read-only GovernanceJudge."""

from datetime import datetime, timezone

from aptdata.governance import (
    AcceptanceCriterion,
    Assignment,
    EvidenceKind,
    EvidenceRecord,
    EvidenceResult,
    EvidenceSource,
    GovernanceJudge,
    Risk,
    SquadDefinition,
    SquadRole,
    WorkPacket,
)

NOW = datetime.now(timezone.utc)


def squad() -> SquadDefinition:
    return SquadDefinition(
        id="squad_judge",
        name="judge",
        roles=[
            SquadRole(id="executor", capability="execute"),
            SquadRole(id="judge", capability="judge"),
        ],
        executor_policy={"allowed": ["test"]},
    )


def packet(*, same_agent: bool = False, missing_judge: bool = False) -> WorkPacket:
    judge_agent = "coder" if same_agent else "reviewer"
    assignments = [
        Assignment(role="executor", agent_id="coder", accepted_at=NOW),
    ]
    if not missing_judge:
        assignments.append(
            Assignment(role="judge", agent_id=judge_agent, accepted_at=NOW)
        )
    return WorkPacket(
        id="wp_judge",
        context_packet_id="cp_judge",
        squad_definition_id="squad_judge",
        objective="judge packet",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-JUDGE", description="verifica", verification="pytest"
            )
        ],
        risk=Risk(level="low", rollback="discard"),
        assignments=assignments,
        state="running",
    )


def evidence(result: EvidenceResult = EvidenceResult.PASS) -> EvidenceRecord:
    return EvidenceRecord(
        id="ev_judge",
        work_packet_id="wp_judge",
        kind=EvidenceKind.TEST,
        claim="output",
        command="pytest -q",
        output_digest="sha256:judge",
        result=result,
        source=EvidenceSource(path="tests/test_governance_judge.py", revision="abc"),
        captured_at=NOW,
        captured_by="qa",
    )


def test_judge_returns_go_for_valid_packet() -> None:
    result = GovernanceJudge("reviewer").judge(packet(), squad(), [evidence()])
    assert result.verdict == "go"
    assert result.independence_check.independent is True
    assert {check.result for check in result.checks} == {EvidenceResult.PASS}


def test_judge_rejects_same_agent_executor_and_judge() -> None:
    result = GovernanceJudge("coder").judge(
        packet(same_agent=True), squad(), [evidence()]
    )
    assert result.verdict == "no_go"
    assert any(f.kind == "security" for f in result.findings)
    assert result.independence_check.independent is False


def test_judge_rejects_missing_required_role() -> None:
    result = GovernanceJudge("reviewer").judge(
        packet(missing_judge=True), squad(), [evidence()]
    )
    assert result.verdict == "no_go"
    assert any(f.kind == "scope" for f in result.findings)


def test_judge_rejects_failed_evidence() -> None:
    result = GovernanceJudge("reviewer").judge(
        packet(), squad(), [evidence(EvidenceResult.FAIL)]
    )
    assert result.verdict == "no_go"
    assert any(f.kind == "regression" for f in result.findings)


def test_judge_marks_inconclusive_evidence_inconclusive() -> None:
    result = GovernanceJudge("reviewer").judge(
        packet(), squad(), [evidence(EvidenceResult.INCONCLUSIVE)]
    )
    assert result.verdict == "inconclusive"


def test_judge_rejects_empty_evidence() -> None:
    result = GovernanceJudge("reviewer").judge(packet(), squad(), [])
    assert result.verdict == "no_go"
    assert any(f.kind == "missing_evidence" for f in result.findings)


def test_judge_is_read_only_for_packet() -> None:
    work = packet()
    before = work.model_dump(mode="json")
    GovernanceJudge("reviewer").judge(work, squad(), [evidence()])
    assert work.model_dump(mode="json") == before
