"""Contract tests for the trusted squad governance models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aptdata.governance import (
    AcceptanceCriterion,
    ContextPacket,
    Domain,
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
    SourceRef,
    SquadDefinition,
    SquadRole,
    Verdict,
    WorkPacket,
)

NOW = datetime.now(timezone.utc)


def squad() -> SquadDefinition:
    return SquadDefinition(
        id="squad_my_universe",
        name="My Universe trusted squad",
        roles=[
            SquadRole(id="po", capability="product_context"),
            SquadRole(id="tech_lead", capability="architecture"),
            SquadRole(id="ui_ux", capability="human_experience"),
            SquadRole(id="qa", capability="verification"),
            SquadRole(id="judge", capability="independent_judgement"),
        ],
        executor_policy={"allowed": ["hermes"]},
    )


def packet() -> WorkPacket:
    return WorkPacket(
        id="wp_001",
        context_packet_id="cp_001",
        squad_definition_id="squad_my_universe",
        objective="Validar um slice read-only",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-001",
                description="O contrato valida",
                verification="pytest tests/test_governance_models.py",
            )
        ],
        risk=Risk(level="low", rollback="descartar o artefato"),
    )


def evidence(result: EvidenceResult = EvidenceResult.PASS) -> EvidenceRecord:
    return EvidenceRecord(
        id="ev_001",
        work_packet_id="wp_001",
        kind=EvidenceKind.TEST,
        claim="A suíte passou",
        command="pytest -q",
        output_digest="sha256:abc",
        result=result,
        source=EvidenceSource(
            path="tests/test_governance_models.py", revision="abc123"
        ),
        captured_at=NOW,
        captured_by="coder",
    )


def test_context_preserves_domain_and_unknowns() -> None:
    context = ContextPacket(
        id="cp_001",
        source=SourceRef(actor="user", channel="my_universe", reference="msg-1"),
        intent="Conhecer meu conhecimento",
        why="Reduzir fricção",
        domain=Domain.PERSONAL,
        unknowns=["qual ritmo ajuda mais"],
    )
    assert context.domain is Domain.PERSONAL
    assert context.unknowns == ["qual ritmo ajuda mais"]


def test_squad_requires_independent_judge() -> None:
    with pytest.raises(ValidationError, match="required judge"):
        SquadDefinition(
            id="squad_bad",
            name="bad",
            roles=[SquadRole(id="executor", capability="run")],
            executor_policy={"allowed": ["hermes"]},
        )


def test_work_packet_transition_is_forward_and_explicit() -> None:
    work = packet()
    assert work.state is PacketState.PROPOSED
    work.transition(PacketState.READY).transition(PacketState.RUNNING)
    assert work.state is PacketState.RUNNING
    with pytest.raises(ValueError, match="invalid WorkPacket transition"):
        work.transition(PacketState.INTEGRATED)


def test_pass_fail_evidence_requires_digest() -> None:
    payload = evidence().model_dump()
    payload["output_digest"] = None
    with pytest.raises(ValidationError, match="output_digest"):
        EvidenceRecord(**payload)


def test_inconclusive_evidence_can_omit_digest() -> None:
    item = evidence(EvidenceResult.INCONCLUSIVE)
    item.output_digest = None
    assert item.result is EvidenceResult.INCONCLUSIVE


def test_judge_requires_independence_and_conditions() -> None:
    base = dict(
        id="jr_001",
        work_packet_id="wp_001",
        judge_agent_id="judge",
        independence_check=IndependenceCheck(
            executor_agent_id="executor", independent=True, reason="different agent"
        ),
        checks=[JudgeCheck(id="J-001", subject="scope", result=EvidenceResult.PASS)],
        created_at=NOW,
    )
    with pytest.raises(ValidationError, match="conditions"):
        JudgeResult(**base, verdict=Verdict.GO_WITH_CONDITIONS)
    with pytest.raises(ValidationError, match="non-independent"):
        invalid = dict(base)
        invalid["independence_check"] = {
            "executor_agent_id": "executor",
            "independent": False,
            "reason": "same agent",
        }
        invalid["verdict"] = Verdict.GO
        JudgeResult(**invalid)
    result = JudgeResult(
        **base,
        verdict=Verdict.GO_WITH_CONDITIONS,
        conditions=["Maestro revisar copy"],
    )
    assert result.verdict is Verdict.GO_WITH_CONDITIONS


def test_judge_no_go_requires_finding() -> None:
    with pytest.raises(ValidationError, match="findings"):
        JudgeResult(
            id="jr_002",
            work_packet_id="wp_001",
            judge_agent_id="judge",
            independence_check=IndependenceCheck(
                executor_agent_id="executor", independent=True, reason="different"
            ),
            checks=[
                JudgeCheck(
                    id="J-001", subject="scope", result=EvidenceResult.FAIL
                )
            ],
            verdict=Verdict.NO_GO,
            created_at=NOW,
        )


def test_maestro_decision_is_separate_record() -> None:
    decision = MaestroDecision(
        id="md_001",
        work_packet_id="wp_001",
        judge_result_id="jr_001",
        action=MaestroAction.APPROVE_WITH_CONDITIONS,
        rationale="Aceito o risco baixo",
        accepted_risks=["copy provisória"],
        actor="lucas",
        created_at=NOW,
    )
    assert decision.actor == "lucas"


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SquadDefinition(
            id="squad_extra",
            name="bad",
            roles=[SquadRole(id="judge", capability="judge")],
            executor_policy={"allowed": ["hermes"]},
            hidden_decision="no",
        )


def test_schemas_are_json_serializable() -> None:
    schema = WorkPacket.model_json_schema()
    assert schema["type"] == "object"
    assert "acceptance_criteria" in schema["properties"]
    assert "state" in schema["properties"]


def test_contract_exports_are_stable() -> None:
    exports = set(__import__("aptdata.governance", fromlist=["__all__"]).__all__)
    assert {
        "ContextPacket",
        "WorkPacket",
        "EvidenceRecord",
        "JudgeResult",
        "MaestroDecision",
    } <= exports
