"""Read-only rehearsal against the repository's real BaseFlow example."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from aptdata.core.system import BaseFlow
from aptdata.governance import (
    AcceptanceCriterion,
    Assignment,
    ContextPacket,
    EvidenceRecord,
    GovernanceJudge,
    GovernanceStore,
    GovernanceWorkflowBinding,
    Risk,
    SourceRef,
    SquadDefinition,
    SquadRole,
    WorkPacket,
)

EXAMPLE_DIR = Path(__file__).parents[1] / "examples" / "01_soccer_medallion"
if str(EXAMPLE_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_DIR))

from flows.soccer_flows import BronzeFlow  # noqa: E402

NOW = datetime.now(timezone.utc)


def setup_binding(store: GovernanceStore) -> GovernanceWorkflowBinding:
    context = ContextPacket(
        id="cp_real_flow",
        source=SourceRef(actor="maestro", channel="test", reference="real-flow"),
        intent="validar um Flow real com governança",
        why="provar rastreabilidade antes de ampliar autonomia",
        domain="development",
        constraints=["exemplo local"],
        unknowns=["não cobre deploy nem provider externo"],
    )
    squad = SquadDefinition(
        id="squad_real_flow",
        name="real-flow-read-only",
        roles=[
            SquadRole(id="executor", capability="run_local_flow"),
            SquadRole(id="judge", capability="audit_records"),
        ],
        executor_policy={"allowed": ["local-test"]},
    )
    packet = WorkPacket(
        id="wp_real_flow",
        context_packet_id=context.id,
        squad_definition_id=squad.id,
        objective="executar BronzeFlow local e registrar evidência",
        scope_in=["examples/01_soccer_medallion/data/raw/matches_mock.csv"],
        scope_out=["rede", "VPS", "My Universe", "alteração de arquivo"],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-REAL-FLOW",
                description="BaseFlow real executa e é recuperável",
                verification="GovernanceStore reabre e Judge retorna GO",
            )
        ],
        risk=Risk(
            level="low",
            hazards=["fixture local pode mudar no futuro"],
            rollback="apagar SQLite temporário",
        ),
        assignments=[
            Assignment(role="executor", agent_id="real_flow_executor", accepted_at=NOW),
            Assignment(role="judge", agent_id="real_flow_judge", accepted_at=NOW),
        ],
        state="ready",
    )
    return GovernanceWorkflowBinding(
        context=context,
        squad=squad,
        packet=packet,
        store=store,
        executor_agent_id="real_flow_executor",
        workspace_id="lucas",
        project_id="aptdata-flow-os",
    )


def test_real_base_flow_is_governed_and_recoverable(tmp_path) -> None:
    path = tmp_path / "real-flow.db"
    with GovernanceStore(path) as store:
        binding = setup_binding(store)
        flow = BronzeFlow(flow_id="soccer_bronze_governed")

        result = binding.run_flow(flow, [], flow_name=flow.flow_id)

        assert len(result) == 1
        assert len(result[0].read()) == 6
        events = store.for_run(binding.last_run_id)
        assert [event.event_type for event in events] == [
            "workflow.started",
            "workflow.completed",
        ]
        assert events[0].run_id == events[1].run_id == binding.last_run_id
        assert events[1].evidence_refs
        evidence = store.get(EvidenceRecord, events[1].evidence_refs[0])
        packet = store.get(WorkPacket, "wp_real_flow")
        squad = store.get(SquadDefinition, "squad_real_flow")
        assert evidence is not None
        assert packet is not None
        assert squad is not None
        assert packet.state.value == "judging"

        judge = GovernanceJudge("real_flow_judge").judge(packet, squad, [evidence])
        assert judge.verdict.value == "go"

    with GovernanceStore(path) as reopened:
        assert reopened.get(WorkPacket, "wp_real_flow") is not None
        assert len(reopened.for_run(binding.last_run_id)) == 2


def test_real_flow_adapter_does_not_require_function_workflow() -> None:
    assert issubclass(BronzeFlow, BaseFlow)
    assert not hasattr(BronzeFlow, "execute")
