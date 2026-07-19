"""Tests for the Event Bus and lifecycle hooks."""

import pytest

from aptdata.core.dataset import IDataset
from aptdata.core.events import ComponentExecutionEvent, EventBus, EventPayload
from aptdata.core.system import BaseComponent
from aptdata.plugins.dataset import InMemoryDataset


class _DummyComponent(BaseComponent):
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return True

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        ds = InMemoryDataset(uri="memory://dummy")
        ds.write([{"dummy": 1}])
        return [ds]


class _FailingComponent(BaseComponent):
    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return True

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        raise ValueError("Simulated component failure")


def test_event_bus_dispatch_success_chronology():
    bus = EventBus()
    events = []

    def listener(event: EventPayload):
        events.append(event)

    bus.subscribe("pre_execute", listener)
    bus.subscribe("on_success", listener)
    bus.subscribe("post_execute", listener)

    comp = _DummyComponent(component_id="dummy")

    class MockContext:
        event_bus = bus

    comp.context = MockContext()

    comp.execute([])

    bus.shutdown()
    assert len(events) == 3
    assert events[0].event_type == "pre_execute"
    assert events[1].event_type == "on_success"
    assert events[1].status == "success"
    assert "memory://dummy" in events[1].io_uris
    assert events[2].event_type == "post_execute"


def test_event_bus_dispatch_failure_chronology():
    bus = EventBus()
    events = []

    def listener(event: EventPayload):
        events.append(event)

    bus.subscribe("pre_execute", listener)
    bus.subscribe("on_failure", listener)
    bus.subscribe("post_execute", listener)

    comp = _FailingComponent(component_id="failer")

    class MockContext:
        event_bus = bus

    comp.context = MockContext()

    with pytest.raises(ValueError, match="Simulated component failure"):
        comp.execute([])

    bus.shutdown()
    assert len(events) == 3
    assert events[0].event_type == "pre_execute"
    assert events[1].event_type == "on_failure"
    assert events[1].status == "failed"
    assert events[1].error_message == "Simulated component failure"
    assert events[2].event_type == "post_execute"


def test_event_bus_fault_tolerance(caplog):
    """Ensure exceptions in listeners do not break dispatch or execution."""
    bus = EventBus()

    def bad_listener(event: EventPayload):
        raise RuntimeError("Bad listener failed!")

    bus.subscribe("pre_execute", bad_listener)

    comp = _DummyComponent(component_id="faulty_listener_test")

    class MockContext:
        event_bus = bus

    comp.context = MockContext()

    # Should not raise
    results = comp.execute([])

    bus.shutdown()
    assert len(results) == 1

    # Warning should be logged
    assert "Bad listener failed!" in caplog.text


def test_event_payload_json_serialization():
    """Ensure payload objects dump correctly to JSON for TUI/MCP."""
    event = ComponentExecutionEvent(
        event_type="on_success",
        component_id="c_1",
        status="done",
        execution_time=1.5,
        io_uris=["s3://bucket/out"],
    )

    json_str = event.model_dump_json()
    assert '"event_type":"on_success"' in json_str
    assert '"component_id":"c_1"' in json_str
    assert '"status":"done"' in json_str
    assert '"execution_time":1.5' in json_str
    assert '"s3://bucket/out"' in json_str
