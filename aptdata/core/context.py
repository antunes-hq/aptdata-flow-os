"""Injectable execution context for state sharing across runs."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import field
from typing import Any

from pydantic.dataclasses import dataclass as pydantic_dataclass

from aptdata.core.events import EventBus, IEventBus
from aptdata.telemetry import TelemetryProvider


class IContext(ABC):
    """Interface for an execution context with logging and telemetry."""

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """Structured logger for this context."""

    @property
    @abstractmethod
    def telemetry(self) -> TelemetryProvider:
        """Telemetry provider for this context."""

    @property
    @abstractmethod
    def event_bus(self) -> IEventBus:
        """Event bus for decoupled communication and observability."""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Return value for *key* or *default* if not present."""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*."""

    @abstractmethod
    def update(self, values: dict[str, Any]) -> None:
        """Merge mapping into memory state."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all state."""


from pydantic import ConfigDict  # noqa: E402


@pydantic_dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class ExecutionContext(IContext):
    """Simple in-memory key/value state container."""

    memory: dict[str, Any] = field(default_factory=dict)
    _logger: logging.Logger | None = field(default=None, init=False, repr=False)
    _telemetry: TelemetryProvider | None = field(default=None, init=False, repr=False)
    _event_bus: IEventBus | None = field(default=None, init=False, repr=False)

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = logging.getLogger("aptdata.context")
        return self._logger

    @property
    def telemetry(self) -> TelemetryProvider:
        if self._telemetry is None:
            self._telemetry = TelemetryProvider.get_instance()
        return self._telemetry

    @property
    def event_bus(self) -> IEventBus:
        if self._event_bus is None:
            self._event_bus = EventBus()
        return self._event_bus

    @event_bus.setter
    def event_bus(self, bus: IEventBus) -> None:
        self._event_bus = bus

    def get(self, key: str, default: Any = None) -> Any:
        return self.memory.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.memory[key] = value

    def update(self, values: dict[str, Any]) -> None:
        self.memory.update(values)

    def clear(self) -> None:
        self.memory.clear()
