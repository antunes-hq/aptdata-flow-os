"""Injectable execution context for state sharing across runs."""

from __future__ import annotations

from dataclasses import field
from typing import Any

from pydantic.dataclasses import dataclass as pydantic_dataclass


@pydantic_dataclass
class ExecutionContext:
    """Simple in-memory key/value state container."""

    memory: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Return value for *key* or *default* if not present."""
        return self.memory.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store *value* under *key*."""
        self.memory[key] = value

    def update(self, values: dict[str, Any]) -> None:
        """Merge mapping into memory state."""
        self.memory.update(values)

    def clear(self) -> None:
        """Remove all state."""
        self.memory.clear()
