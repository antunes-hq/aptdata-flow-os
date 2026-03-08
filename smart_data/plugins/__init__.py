"""Plugin registry for smart-data systems.

Third-party adapters (Spark, REST APIs, databases, …) register concrete
implementations of :class:`~smart_data.core.system.ISystem` here
so that the CLI can discover and instantiate them by name.

Usage
-----
Register a system::

    from smart_data.plugins import registry
    from my_package import MySystem

    registry.register("my_system", MySystem)

Look up a system by name::

    system_cls = registry.get("my_system")
    if system_cls is not None:
        system_cls(system_id="my_system").run()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from smart_data.core.system import ISystem


class _SystemRegistry:
    """Simple name → system-class mapping."""

    def __init__(self) -> None:
        self._store: dict[str, type[ISystem]] = {}

    def register(self, name: str, system_cls: type[ISystem]) -> None:
        """Register *system_cls* under *name*.

        Parameters
        ----------
        name:
            Unique identifier used on the CLI (e.g. ``"pipeline_x"``).
        system_cls:
            A concrete subclass of :class:`~smart_data.core.system.ISystem`.
        """
        self._store[name] = system_cls

    def get(self, name: str) -> type[ISystem] | None:
        """Return the system class registered under *name*, or ``None``."""
        return self._store.get(name)

    def list_systems(self) -> list[str]:
        """Return a sorted list of all registered system names."""
        return sorted(self._store)


#: Global singleton registry – import this in adapter modules.
registry = _SystemRegistry()

__all__ = ["registry", "_SystemRegistry"]
