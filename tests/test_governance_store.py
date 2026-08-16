"""Durability and atomicity tests for governance records."""

from datetime import datetime, timezone

import pytest

from aptdata.governance import (
    AcceptanceCriterion,
    ContextPacket,
    EvidenceKind,
    EvidenceRecord,
    EvidenceResult,
    EvidenceSource,
    GovernanceStore,
    SourceRef,
    WorkPacket,
)

NOW = datetime.now(timezone.utc)


def context() -> ContextPacket:
    return ContextPacket(
        id="cp_store",
        source=SourceRef(actor="user", channel="test", reference="fixture"),
        intent="testar durabilidade",
        why="não perder registro",
        domain="personal",
    )


def packet() -> WorkPacket:
    return WorkPacket(
        id="wp_store",
        context_packet_id="cp_store",
        squad_definition_id="squad_store",
        objective="testar store",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-STORE",
                description="salva e lê",
                verification="pytest",
            )
        ],
        risk={"level": "low", "rollback": "delete fixture"},
    )


def evidence(record_id: str = "ev_store") -> EvidenceRecord:
    return EvidenceRecord(
        id=record_id,
        work_packet_id="wp_store",
        kind=EvidenceKind.TEST,
        claim="teste passou",
        command="pytest -q",
        output_digest="sha256:test",
        result=EvidenceResult.PASS,
        source=EvidenceSource(path="tests/test_governance_store.py", revision="abc"),
        captured_at=NOW,
        captured_by="qa",
    )


def test_round_trip_and_latest_version(tmp_path) -> None:
    path = tmp_path / "governance.db"
    with GovernanceStore(path) as store:
        store.append(context())
        store.append(packet())
        store.append(evidence())
        assert store.count() == 3
        assert store.get(ContextPacket, "cp_store").intent == "testar durabilidade"
        assert len(store.for_work_packet("wp_store")) == 1

    with GovernanceStore(path) as reopened:
        assert reopened.count() == 3
        assert reopened.get(WorkPacket, "wp_store").objective == "testar store"


def test_duplicate_identity_version_is_rejected(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        store.append(context())
        with pytest.raises(ValueError, match="already exists"):
            store.append(context())
        assert store.count() == 1


def test_append_many_is_atomic(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        with pytest.raises(ValueError, match="already exists"):
            store.append_many([context(), context()])
        assert store.count() == 0


def test_versioned_records_are_append_only(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        first = evidence()
        second = evidence("ev_store_v2").model_copy(update={"version": 2})
        store.append_many([first, second])
        assert store.get(EvidenceRecord, "ev_store").version == 1
        assert store.get(EvidenceRecord, "ev_store_v2", version=2).version == 2


def test_unknown_record_type_is_rejected(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        with pytest.raises(TypeError, match="unsupported"):
            store.append(object())


def test_work_packet_filter_is_structural(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        store.append(evidence())
        assert store.for_work_packet("missing") == []
        rows = store.for_work_packet("wp_store")
        assert rows[0]["record_type"] == "evidence_records"
        assert "sha256:test" in rows[0]["payload"]


def test_store_does_not_mutate_source_model(tmp_path) -> None:
    item = context()
    with GovernanceStore(tmp_path / "governance.db") as store:
        store.append(item)
    assert item.id == "cp_store"
    assert item.domain.value == "personal"


def test_store_requires_typed_validated_records(tmp_path) -> None:
    with GovernanceStore(tmp_path / "governance.db") as store:
        with pytest.raises(TypeError):
            store.append({"id": "not-a-model"})
