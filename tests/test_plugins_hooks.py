"""Tests for the EventBus→pluggy bridge (ADR-002 §2.1).

Covers:
* :func:`create_plugin_manager` returns a :class:`pluggy.PluginManager`
  wired to the ``aptdata`` namespace with the four lifecycle hookspecs;
* :class:`PluggyEventBusBridge` subscribes to the EventBus for the four
  event types and forwards each dispatched event to the matching pluggy
  hook — synchronously, in dispatch order;
* hookimpl exceptions are caught and logged (the EventBus worker thread
  is already fault-tolerant; a misbehaving plugin must not crash it);
* the four lifecycle event types are exactly the ones emitted by
  :class:`aptdata.core.system.BaseComponent`.
"""

from __future__ import annotations

import logging
from typing import Any

import pluggy

from aptdata.core.events import ComponentExecutionEvent, EventBus, EventPayload
from aptdata.plugins.hooks import (
    HOOK_NAMESPACE,
    LIFECYCLE_EVENT_TYPES,
    LifecycleHookSpecs,
    PluggyEventBusBridge,
    create_plugin_manager,
    hookimpl,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _RecordingPlugin:
    """A hookimpl plugin that records every call it receives."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, EventPayload]] = []

    @hookimpl
    def pre_execute(self, event: Any) -> None:
        self.calls.append(("pre_execute", event))

    @hookimpl
    def on_success(self, event: Any) -> None:
        self.calls.append(("on_success", event))

    @hookimpl
    def on_failure(self, event: Any) -> None:
        self.calls.append(("on_failure", event))

    @hookimpl
    def post_execute(self, event: Any) -> None:
        self.calls.append(("post_execute", event))


class _BoomPlugin:
    """A hookimpl plugin whose ``on_success`` raises — used to test fault-tolerance."""

    def __init__(self) -> None:
        self.invoked = False

    @hookimpl
    def on_success(self, event: Any) -> None:
        self.invoked = True
        raise RuntimeError("boom from hookimpl")


def _event(event_type: str, component_id: str = "c1") -> ComponentExecutionEvent:
    return ComponentExecutionEvent(
        event_type=event_type,
        component_id=component_id,
        status="ok",
    )


# ---------------------------------------------------------------------------
# create_plugin_manager
# ---------------------------------------------------------------------------


class TestCreatePluginManager:
    def test_returns_pluggy_plugin_manager(self):
        pm = create_plugin_manager()
        assert isinstance(pm, pluggy.PluginManager)

    def test_uses_aptdata_namespace(self):
        pm = create_plugin_manager()
        assert pm.project_name == HOOK_NAMESPACE

    def test_lifecycle_hookspecs_registered(self):
        pm = create_plugin_manager()
        # pluggy exposes hookspecs as attributes on pm.hook
        for hook_name in LIFECYCLE_EVENT_TYPES:
            assert hasattr(pm.hook, hook_name), f"hookspec {hook_name!r} missing"

    def test_lifecycle_event_types_match_base_component(self):
        """The four event types the bridge forwards must be exactly the ones
        emitted by BaseComponent (pre/on_success/on_failure/post_execute)."""
        assert set(LIFECYCLE_EVENT_TYPES) == {
            "pre_execute",
            "on_success",
            "on_failure",
            "post_execute",
        }

    def test_lifecycle_hookspecs_is_a_class(self):
        """LifecycleHookSpecs is a plain class container — instantiable for tests."""
        spec = LifecycleHookSpecs()
        assert callable(spec.pre_execute)
        assert callable(spec.on_success)
        assert callable(spec.on_failure)
        assert callable(spec.post_execute)


# ---------------------------------------------------------------------------
# PluggyEventBusBridge — forwarding
# ---------------------------------------------------------------------------


class TestPluggyEventBusBridge:
    def test_forwards_each_lifecycle_event_to_pluggy(self):
        bus = EventBus()
        plugin = _RecordingPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        try:
            for event_type in LIFECYCLE_EVENT_TYPES:
                bus.dispatch(_event(event_type))
            bus.shutdown()
        finally:
            # shutdown is idempotent enough for the test path
            pass

        names = [name for name, _ in plugin.calls]
        assert names == list(LIFECYCLE_EVENT_TYPES)

    def test_forwards_payload_intact(self):
        bus = EventBus()
        plugin = _RecordingPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        evt = ComponentExecutionEvent(
            event_type="on_success",
            component_id="comp-42",
            status="success",
            execution_time=1.23,
            io_uris=["s3://bucket/out"],
        )
        bus.dispatch(evt)
        bus.shutdown()

        assert len(plugin.calls) == 1
        name, forwarded = plugin.calls[0]
        assert name == "on_success"
        assert forwarded is evt
        assert forwarded.component_id == "comp-42"
        assert forwarded.execution_time == 1.23

    def test_unknown_event_type_not_forwarded(self):
        """Events whose type is not a lifecycle hook are silently ignored."""
        bus = EventBus()
        plugin = _RecordingPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        bus.dispatch(
            ComponentExecutionEvent(
                event_type="some_custom_event",
                component_id="c",
                status="ok",
            )
        )
        bus.shutdown()

        assert plugin.calls == []

    def test_hookimpl_exception_does_not_propagate(self, caplog):
        """A raising hookimpl is logged and swallowed — the worker thread survives."""
        bus = EventBus()
        plugin = _BoomPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        with caplog.at_level(logging.WARNING, logger="aptdata.plugins.hooks"):
            bus.dispatch(_event("on_success"))
            bus.shutdown()

        assert plugin.invoked is True
        assert any(
            "pluggy hook 'on_success' failed" in rec.message for rec in caplog.records
        )

    def test_accepts_pre_built_plugin_manager(self):
        """A caller can pass in a pre-configured PluginManager (e.g. one that
        already loaded third-party plugins from entry points)."""
        bus = EventBus()
        pm = create_plugin_manager()
        plugin = _RecordingPlugin()
        pm.register(plugin)
        bridge = PluggyEventBusBridge(bus, plugin_manager=pm)

        assert bridge.plugin_manager is pm
        bus.dispatch(_event("pre_execute"))
        bus.shutdown()

        assert len(plugin.calls) == 1
        assert plugin.calls[0][0] == "pre_execute"

    def test_event_bus_property_returns_wrapped_bus(self):
        bus = EventBus()
        bridge = PluggyEventBusBridge(bus)
        assert bridge.event_bus is bus
        bus.shutdown()

    def test_subscribes_to_all_four_lifecycle_types(self):
        """The bridge registers a listener for every lifecycle event type on the bus."""
        # We can't peek into the private _listeners dict of EventBus cleanly,
        # but we can verify by dispatching each one and checking forwarding.
        bus = EventBus()
        plugin = _RecordingPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        for event_type in LIFECYCLE_EVENT_TYPES:
            bus.dispatch(_event(event_type, component_id=event_type))
        bus.shutdown()

        # No event lost, no event duplicated
        assert len(plugin.calls) == len(LIFECYCLE_EVENT_TYPES)
        assert {name for name, _ in plugin.calls} == set(LIFECYCLE_EVENT_TYPES)


# ---------------------------------------------------------------------------
# Integration with BaseComponent — end-to-end EventBus → pluggy
# ---------------------------------------------------------------------------


class TestBridgeWithBaseComponent:
    def test_real_component_execution_invokes_hookimpls(self):
        """End-to-end: a BaseComponent executing through a real System/Context
        fires lifecycle events on the EventBus, which the bridge forwards to
        a registered pluggy hookimpl."""
        from aptdata.core.context import ExecutionContext
        from aptdata.core.dataset import IDataset
        from aptdata.core.system import BaseComponent
        from aptdata.plugins.dataset import InMemoryDataset

        class _OkComponent(BaseComponent):
            def validate_inputs(self, inputs: list[IDataset]) -> bool:
                return True

            def execute(self, inputs: list[IDataset]) -> list[IDataset]:
                ds = InMemoryDataset(uri="memory://ok")
                ds.write([{"ok": 1}])
                return [ds]

        bus = EventBus()
        plugin = _RecordingPlugin()
        bridge = PluggyEventBusBridge(bus)
        bridge.plugin_manager.register(plugin)

        ctx = ExecutionContext()
        ctx.event_bus = bus  # type: ignore[assignment]  # EventBus satisfies IEventBus

        comp = _OkComponent(component_id="ok-comp")
        comp.context = ctx  # type: ignore[assignment]  # ExecutionContext satisfies IContext
        comp.execute([])

        bus.shutdown()

        names = [name for name, _ in plugin.calls]
        # pre_execute → on_success → post_execute (no on_failure on the happy path)
        assert names == ["pre_execute", "on_success", "post_execute"]
        # The component_id travels through
        assert all(e.component_id == "ok-comp" for _, e in plugin.calls)
