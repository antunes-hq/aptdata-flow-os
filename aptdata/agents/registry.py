"""AgentRegistry — the single source of truth for agent backends.

Loads ``agents.yaml`` once and resolves backends by id or capability,
instantiating the right adapter for each :class:`AgentSpec`. This replaces
the three previously divergent registries (multiverso.json, the plugin's
routing ``schema.yaml`` and ``app.py``'s ``DEFAULT_CONFIG``).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from aptdata.agents.base import AgentResponse, AgentSpec, BaseAgent, IAgent
from aptdata.agents.cli_agents import ClaudeCodeAgent, OpenCodeAgent
from aptdata.agents.openclaw import OpenClawAgent

logger = logging.getLogger(__name__)

#: adapter kind -> implementing class. Unknown kinds (e.g. docker_compose) fall
#: back to :class:`_PlaceholderAgent`.
ADAPTERS: dict[str, type[BaseAgent]] = {
    "openclaw": OpenClawAgent,
    "claude_code": ClaudeCodeAgent,
    "opencode": OpenCodeAgent,
}


class _PlaceholderAgent(BaseAgent):
    """Stand-in for a backend kind that has no adapter yet.

    Keeps ``list``/``health`` working for every registered backend while
    ``send`` fails gracefully instead of crashing the registry.
    """

    type = "placeholder"

    def send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        return AgentResponse(
            ok=False,
            agent_id=self.id,
            error=f"no adapter implemented for type '{self.spec.type}' yet",
        )


def _build_agent(spec: AgentSpec) -> IAgent:
    adapter = ADAPTERS.get(spec.type, _PlaceholderAgent)
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
