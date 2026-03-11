"""Event Bus and Lifecycle Hooks for observing system execution."""

from __future__ import annotations

import logging
import queue
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class EventPayload(BaseModel):
    """Base class for all events emitted by the framework.
    All events must be serializable to JSON Lines for TUI/MCP."""

    model_config = ConfigDict(extra="allow")

    event_type: str = Field(..., description="The type/topic of the event.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred.",
    )


class ComponentExecutionEvent(EventPayload):
    """Event emitted during a component's lifecycle."""

    component_id: str
    status: str
    execution_time: float | None = None
    io_uris: list[str] = Field(default_factory=list)
    error_message: str | None = None


class IEventBus(ABC):
    """Interface for an Event Bus."""

    @abstractmethod
    def subscribe(
        self, event_type: str, listener: Callable[[EventPayload], None]
    ) -> None:
        """Register a listener for a specific event type."""
        pass

    @abstractmethod
    def dispatch(self, event: EventPayload) -> None:
        """Dispatch an event asynchronously or non-blocking."""
        pass


class EventBus(IEventBus):
    """An asynchronous, non-blocking event bus for the core system.
    Dispatches events using a background thread and a thread-safe queue.
    Exceptions in listeners are caught and logged as warnings to prevent
    blocking data processing or the background thread."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[EventPayload], None]]] = {}
        self._queue: queue.Queue[EventPayload] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def subscribe(
        self, event_type: str, listener: Callable[[EventPayload], None]
    ) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(listener)

    def dispatch(self, event: EventPayload) -> None:
        """Enqueue event for background dispatch. Non-blocking."""
        self._queue.put(event)

    def _worker(self) -> None:
        """Background worker to process events from the queue."""
        while not self._stop_event.is_set():
            try:
                # Use a timeout to allow checking _stop_event periodically
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            listeners = self._listeners.get(event.event_type, [])
            for listener in listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.warning(
                        f"Listener {getattr(listener, '__name__', str(listener))} "
                        f"failed on event {event.event_type}: {e}"
                    )
            self._queue.task_done()

    def shutdown(self, timeout: float | None = None) -> None:
        """Wait for all events to be processed and shut down the worker thread."""
        self._queue.join()
        self._stop_event.set()
        self._worker_thread.join(timeout=timeout)
