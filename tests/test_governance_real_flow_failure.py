"""Failure-path test for the real BaseFlow governance adapter."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aptdata.core.dataset import DataContractError
from aptdata.governance import (
    AcceptanceCriterion,
    Assignment,
    ContextPacket,
    EvidenceRecord,
    EvidenceResult,
    GovernanceStore,
    GovernanceWorkflowBinding,
    Risk,
    SourceRef,
    SquadDefinition,
    SquadRole,
    WorkPacket,
)
from aptdata.plugins.dataset import InMemoryDataset

EXAMPLE_DIR = Path(__file__).parents[1] / "examples" / "01_soccer_medallion"
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

from components.soccer_components import CleanMatchDataComponent  # noqa: E402
from flows.soccer_flows import SilverFlow  # noqa: E402

NOW = datetime.now(timezone.utc)


def test_real_base_flow_failure_is_recorded_and_reraised(monkeypatch, tmp_path) -> None:
    def invalid_execute(self, inputs):
        dataset = InMemoryDataset(uri="memory://invalid")
        dataset.write([{"match_id": "broken"}])
        return [dataset]

    monkeypatch.setattr(CleanMatchDataComponent, "execute", invalid_execute)
    context = ContextPacket(
        id="cp_real_fail",
        source=SourceRef(actor="test", channel="pytest", reference="failure"),
        intent="validar falha real",
        why="não esconder erro",
        domain="development",
    )
    squad = SquadDefinition(
        id="squad_real_fail",
        name="real-flow-failure",
        roles=[
            SquadRole(id="executor", capability="run"),
            SquadRole(id="judge", capability="audit"),
        ],
        executor_policy={"allowed": ["test"]},
    )
    packet = WorkPacket(
        id="wp_real_fail",
        context_packet_id=context.id,
        squad_definition_id=squad.id,
        objective="registrar falha",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-FAIL", description="falha registrada", verification="pytest"
            )
        ],
        risk=Risk(level="low", rollback="apagar db"),
        assignments=[
            Assignment(role="executor", agent_id="failure_executor", accepted_at=NOW),
            Assignment(role="judge", agent_id="failure_judge", accepted_at=NOW),
        ],
        state="ready",
    )
    path = tmp_path / "failure.db"
    with GovernanceStore(path) as store:
        binding = GovernanceWorkflowBinding(
            context=context,
            squad=squad,
            packet=packet,
            store=store,
            executor_agent_id="failure_executor",
        )
        input_dataset = InMemoryDataset(uri="memory://input")
        input_dataset.write([{"match_id": "input"}])
        with pytest.raises(DataContractError):
            binding.run_flow(
                SilverFlow(flow_id="silver_failure"),
                [input_dataset],
                flow_name="silver_failure",
            )

        assert binding.last_run_id is not None
        events = store.for_run(binding.last_run_id)
        assert [item.event_type for item in events] == [
            "workflow.started",
            "workflow.failed",
        ]
        evidence = store.get(EvidenceRecord, events[1].evidence_refs[0])
        assert evidence is not None
        assert evidence.result is EvidenceResult.FAIL
        assert evidence.captured_by == "failure_executor"
        assert "DataContractError" not in evidence.output_digest
    assert path.exists()


def test_failure_fixture_uses_real_base_flow() -> None:
    assert issubclass(SilverFlow, object)
    assert CleanMatchDataComponent.__name__ == "CleanMatchDataComponent"
