"""Tests for durable FlowEvent correlation in governed workflow runs."""

from uuid import uuid4

from aptdata.events.models import FlowEvent
from aptdata.governance import GovernanceStore


def event(event_type: str, run_id: str) -> FlowEvent:
    return FlowEvent(
        event_id=uuid4(),
        schema_version=1,
        event_type=event_type,
        workspace_id="lucas",
        project_id="aptdata-flow-os",
        run_id=run_id,
        severity="info",
        human_summary=f"{event_type} for {run_id}",
        metadata={"work_packet_id": "wp_events"},
    )


def test_store_round_trips_flow_event_and_filters_by_run(tmp_path) -> None:
    path = tmp_path / "events.db"
    first = event("workflow.started", "run-001")
    second = event("workflow.completed", "run-001")
    unrelated = event("workflow.started", "run-002")

    with GovernanceStore(path) as store:
        store.append_event(first)
        store.append_event(second)
        store.append_event(unrelated)

    with GovernanceStore(path) as reopened:
        restored = reopened.get_event(first.event_id)
        assert restored == first
        events = reopened.for_run("run-001")
        assert [item.event_type for item in events] == [
            "workflow.started",
            "workflow.completed",
        ]


def test_store_rejects_duplicate_flow_event(tmp_path) -> None:
    item = event("workflow.started", "run-duplicate")
    with GovernanceStore(tmp_path / "events.db") as store:
        store.append_event(item)
        try:
            store.append_event(item)
        except ValueError as exc:
            assert "event already exists" in str(exc)
        else:
            raise AssertionError("duplicate event must be rejected")


def test_flow_event_is_immutable() -> None:
    item = event("workflow.started", "run-immutable")
    try:
        item.run_id = "changed"
    except Exception as exc:
        assert "frozen" in str(exc).lower()
    else:
        raise AssertionError("FlowEvent must remain immutable")
