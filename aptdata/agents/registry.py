"""AgentRegistry — the single source of truth for agent backends.

Loads ``agents.yaml`` once and resolves backends by id or capability,
instantiating the right adapter for each :class:`AgentSpec`. This replaces
the three previously divergent registries (multiverso.json, the plugin's
routing ``schema.yaml`` and ``app.py``'s ``DEFAULT_CONFIG``).

Adapter discovery (ADR-002 §2.1)
--------------------------------
Backends are no longer hard-coded in this module. Instead, the registry
discovers them through Python entry points under the ``aptdata.agents``
group (declared in ``pyproject.toml`` and any third-party package). A
third party registers a new backend by adding::

    [project.entry-points."aptdata.agents"]
    meu_backend = "meu_pacote.adapters:MeuAgent"

Discovery is **lazy** (first call wins) and **fault-tolerant**: an entry
point that fails to load is logged as a warning and skipped, so a broken
third-party plugin never crashes the registry. Unknown ``spec.type``
values fall back to :class:`_PlaceholderAgent`, which keeps ``list`` /
``health`` working while ``send`` fails gracefully.
"""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from aptdata.agents.base import AgentResponse, AgentSpec, BaseAgent, IAgent

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint

logger = logging.getLogger(__name__)

#: Entry-point group that maps ``spec.type`` → adapter class. Declared in
#: ``pyproject.toml`` for built-ins; third-party packages declare their own.
AGENT_ENTRY_POINT_GROUP = "aptdata.agents"

#: Lazy cache of discovered adapters (``spec.type`` → adapter class).
#: Populated on first access by :func:`_discover_adapters`; reset by
#: :func:`_reset_adapters_cache` (mostly a test seam).
_ADAPTERS_CACHE: dict[str, type[BaseAgent]] | None = None


class _PlaceholderAgent(BaseAgent):
    """Stand-in for a backend kind that has no adapter yet.

    Keeps ``list``/``health`` working for every registered backend while
    ``send`` fails gracefully instead of crashing the registry.
    """

    type = "placeholder"

    def _do_send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        return AgentResponse(
            ok=False,
            agent_id=self.id,
            error=f"no adapter implemented for type '{self.spec.type}' yet",
        )


def _discover_adapters() -> dict[str, type[BaseAgent]]:
    """Discover agent adapters via entry points (group ``aptdata.agents``).

    Returns a ``{type: adapter_class}`` mapping. Broken entry points are
    logged as warnings and skipped — they never raise. The result is
    cached on first call; use :func:`_reset_adapters_cache` to force
    re-discovery (test seam).
    """
    global _ADAPTERS_CACHE
    if _ADAPTERS_CACHE is not None:
        return _ADAPTERS_CACHE

    adapters: dict[str, type[BaseAgent]] = {}
    try:
        eps: list[EntryPoint] = list(entry_points(group=AGENT_ENTRY_POINT_GROUP))
    except Exception as exc:  # noqa: BLE001 — never crash the registry
        logger.warning(
            "Failed to read entry points group '%s': %s",
            AGENT_ENTRY_POINT_GROUP,
            exc,
        )
        _ADAPTERS_CACHE = adapters
        return adapters

    for ep in eps:
        try:
            adapter_cls = ep.load()
        except Exception as exc:  # noqa: BLE001 — broken plugin ≠ broken registry
            logger.warning(
                "Failed to load agent adapter '%s' (value=%s): %s",
                ep.name,
                ep.value,
                exc,
            )
            continue
        if not isinstance(adapter_cls, type) or not issubclass(adapter_cls, BaseAgent):
            logger.warning(
                "Entry point '%s' for '%s' is not a BaseAgent subclass: %r",
                ep.name,
                AGENT_ENTRY_POINT_GROUP,
                adapter_cls,
            )
            continue
        adapters[ep.name] = adapter_cls
        logger.debug("Discovered agent adapter '%s' -> %s", ep.name, ep.value)

    _ADAPTERS_CACHE = adapters
    return adapters


def _reset_adapters_cache() -> None:
    """Clear the adapter discovery cache.

    Intended for tests that need to monkeypatch ``entry_points`` and
    re-trigger discovery. Not part of the public API.
    """
    global _ADAPTERS_CACHE
    _ADAPTERS_CACHE = None


def _build_agent(spec: AgentSpec) -> IAgent:
    adapters = _discover_adapters()
    adapter = adapters.get(spec.type, _PlaceholderAgent)
    return adapter(spec)


class AgentRegistry:
    """Holds the declarative specs and hands out instantiated adapters."""

    def __init__(self, specs: list[AgentSpec]) -> None:
        self._specs: dict[str, AgentSpec] = {s.id: s for s in specs}

    # -- construction -------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> AgentRegistry:
        """Load a registry from an ``agents.yaml`` file."""
        path = Path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        agents = raw.get("agents", raw)  # tolerate top-level list or mapping
        specs = cls._coerce_specs(agents)
        logger.debug("Loaded %d agent specs from %s", len(specs), path)
        return cls(specs)

    @staticmethod
    def _coerce_specs(agents: Any) -> list[AgentSpec]:
        specs: list[AgentSpec] = []
        if isinstance(agents, dict):
            for agent_id, body in agents.items():
                body = dict(body or {})
                body.setdefault("id", agent_id)
                specs.append(AgentSpec(**body))
        elif isinstance(agents, list):
            specs = [AgentSpec(**dict(body)) for body in agents]
        return specs

    # -- queries ------------------------------------------------------------

    def specs(self, *, include_disabled: bool = True) -> list[AgentSpec]:
        items = self._specs.values()
        if include_disabled:
            return list(items)
        return [s for s in items if s.enabled]

    def get(self, agent_id: str) -> IAgent:
        if agent_id not in self._specs:
            raise KeyError(f"Agent '{agent_id}' is not registered.")
        return _build_agent(self._specs[agent_id])

    def spec(self, agent_id: str) -> AgentSpec:
        if agent_id not in self._specs:
            raise KeyError(f"Agent '{agent_id}' is not registered.")
        return self._specs[agent_id]

    def by_capability(
        self, capability: str, *, enabled_only: bool = True
    ) -> list[IAgent]:
        """Return agents that advertise ``capability``, strongest weight first."""
        matches = [
            s
            for s in self._specs.values()
            if capability in s.capabilities and (s.enabled or not enabled_only)
        ]
        matches.sort(key=lambda s: s.weight, reverse=True)
        return [_build_agent(s) for s in matches]

    def resolve(self, capability: str) -> IAgent | None:
        """Pick the single best agent for a capability, if any."""
        agents = self.by_capability(capability)
        return agents[0] if agents else None

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, agent_id: object) -> bool:
        return agent_id in self._specs


# ---------------------------------------------------------------------------
# PEP 562 — lazy module attribute ``ADAPTERS``
#
# ``ADAPTERS`` is preserved as a public symbol for backwards-compat with
# callers that import it directly (``from aptdata.agents.registry import
# ADAPTERS``). It returns the lazily-discovered mapping — the hard-coded
# dict is gone, entry points are the single source of truth (ADR-002 §4.1).
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> Any:
    if name == "ADAPTERS":
        return _discover_adapters()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
