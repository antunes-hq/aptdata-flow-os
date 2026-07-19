"""Pluggy hookspecs and EventBus→pluggy bridge (ADR-002 §2.1).

The framework's lifecycle events (``pre_execute`` / ``on_success`` /
``on_failure`` / ``post_execute``) are already emitted on the
:class:`~aptdata.core.events.EventBus` by
:class:`~aptdata.core.system.BaseComponent`. This module mirrors them as
**pluggy hookspecs**, so external plugins discovered via entry points
(group ``aptdata.plugins``) can react to the lifecycle without coupling
directly to the EventBus internals.

Design
------
* :data:`hookspec` / :data:`hookimpl` — markers under the
  ``"aptdata"`` namespace (the same convention pytest uses).
* :class:`LifecycleHookSpecs` — the four lifecycle hookspecs. Hosts
  register them on a :class:`pluggy.PluginManager` via
  :func:`create_plugin_manager`.
* :class:`PluggyEventBusBridge` — subscribes to the EventBus for the four
  event types and re-emits each event as the matching pluggy hook call.
  Hookimpl exceptions are swallowed (the EventBus worker is already
  fault-tolerant; we don't want a misbehaving plugin to crash the worker
  thread). This keeps the existing "governança invisível" contract from
  ADR-001 intact.

Usage
-----
Register a third-party hookimpl::

    from aptdata.plugins.hooks import hookimpl

    class MyPlugin:
        @hookimpl
        def on_success(self, event):
            print(f"component {event.component_id} succeeded")

Wire the bridge once at system start-up::

    from aptdata.plugins.hooks import PluggyEventBusBridge

    bridge = PluggyEventBusBridge(system_context.event_bus)
    bridge.plugin_manager.register(MyPlugin())
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from aptdata.core.events import EventBus, EventPayload

logger = logging.getLogger(__name__)

#: Pluggy namespace for all aptdata hooks. Third-party ``@hookimpl`` markers
#: MUST use the same namespace to be discovered by :func:`create_plugin_manager`.
HOOK_NAMESPACE = "aptdata"

#: Marker for hook specifications (used in :class:`LifecycleHookSpecs`).
hookspec = pluggy.HookspecMarker(HOOK_NAMESPACE)

#: Marker for hook implementations (used by third-party plugins).
hookimpl = pluggy.HookimplMarker(HOOK_NAMESPACE)

#: The four lifecycle event types emitted by ``BaseComponent`` (ADR-001).
#: Kept in dispatch order: ``pre_execute`` → (``on_success`` | ``on_failure``)
#: → ``post_execute``.
LIFECYCLE_EVENT_TYPES: tuple[str, ...] = (
    "pre_execute",
    "on_success",
    "on_failure",
    "post_execute",
)


class LifecycleHookSpecs:
    """Hook specifications for the component lifecycle (ADR-001 / ADR-002 §2.1).

    Each hookspec mirrors an :class:`~aptdata.core.events.EventBus` event
    type emitted by :class:`~aptdata.core.system.BaseComponent`. The single
    ``event`` argument is the :class:`~aptdata.core.events.ComponentExecutionEvent`
    instance already dispatched on the bus, so plugins see the same payload
    as in-process listeners.
    """

    @hookspec  # type: ignore[misc]
    def pre_execute(self, event: Any) -> None:
        """Fired before a component starts executing (status=pending)."""

    @hookspec  # type: ignore[misc]
    def on_success(self, event: Any) -> None:
        """Fired after a component completes successfully."""

    @hookspec  # type: ignore[misc]
    def on_failure(self, event: Any) -> None:
        """Fired when a component raises during execution."""

    @hookspec  # type: ignore[misc]
    def post_execute(self, event: Any) -> None:
        """Fired after execution settles (success or failure)."""


def create_plugin_manager() -> pluggy.PluginManager:
    """Build a fresh :class:`pluggy.PluginManager` wired to aptdata's hooks.

    The manager has the ``"aptdata"`` namespace and the
    :class:`LifecycleHookSpecs` registered. Third-party plugins discovered
    via entry points (group ``aptdata.plugins``) can be registered on the
    returned manager.
    """
    pm = pluggy.PluginManager(HOOK_NAMESPACE)
    pm.add_hookspecs(LifecycleHookSpecs)
    return pm


class PluggyEventBusBridge:
    """Bridge EventBus events to pluggy hook calls.

    Subscribes to the four lifecycle event types on the wrapped
    :class:`~aptdata.core.events.EventBus` and forwards each dispatched
    event to the corresponding pluggy hook on the wrapped
    :class:`pluggy.PluginManager`.

    The bridge is **best-effort**: hookimpl exceptions are caught and
    logged as warnings (matching the EventBus's own fault-tolerance
    contract — a misbehaving plugin must not crash the worker thread).

    Parameters
    ----------
    event_bus:
        The EventBus to subscribe to. Events of types listed in
        :data:`LIFECYCLE_EVENT_TYPES` are forwarded.
    plugin_manager:
        Optional pre-built :class:`pluggy.PluginManager` (e.g. one that
        already loaded third-party plugins from entry points). When
        omitted, a fresh one is created via :func:`create_plugin_manager`.
    """

    def __init__(
        self,
        event_bus: EventBus,
        plugin_manager: pluggy.PluginManager | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._pm = plugin_manager or create_plugin_manager()
        for event_type in LIFECYCLE_EVENT_TYPES:
            self._event_bus.subscribe(event_type, self._forward_to_pluggy)

    @property
    def event_bus(self) -> EventBus:
        """The wrapped EventBus."""
        return self._event_bus

    @property
    def plugin_manager(self) -> pluggy.PluginManager:
        """The pluggy PluginManager hooks are forwarded to."""
        return self._pm

    def _forward_to_pluggy(self, event: EventPayload) -> None:
        """Forward one EventBus event to the matching pluggy hook.

        Exceptions in hookimpls are caught and logged — never propagated
        to the EventBus worker thread.
        """
        hook_name = event.event_type
        hook = getattr(self._pm.hook, hook_name, None)
        if hook is None:  # pragma: no cover - defensive, all 4 are registered
            return
        try:
            hook(event=event)
        except Exception as exc:  # noqa: BLE001 — see class docstring
            logger.warning(
                "pluggy hook '%s' failed on event %s: %s",
                hook_name,
                getattr(event, "component_id", "?"),
                exc,
            )


__all__ = [
    "HOOK_NAMESPACE",
    "LIFECYCLE_EVENT_TYPES",
    "LifecycleHookSpecs",
    "PluggyEventBusBridge",
    "create_plugin_manager",
    "hookimpl",
    "hookspec",
]
