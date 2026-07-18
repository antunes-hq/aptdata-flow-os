"""Agents — a uniform interface over heterogeneous AI/automation backends.

This module lets aptdata talk to many kinds of agent backends (OpenClaw
workers, OpenCode, Claude Code, plain HTTP APIs) through a single, stable
contract, mirroring the :mod:`aptdata.integrations` pattern.

* :class:`AgentSpec` — declarative description of one backend (loaded from
  ``agents.yaml``); the single source of truth that replaces the three
  divergent registries (multiverso.json, plugin schema.yaml, app.py).
* :class:`IAgent` / :class:`BaseAgent` — the interface every adapter
  implements, following the project's ``IXxx`` -> ``BaseXxx`` convention.
* :class:`AgentResponse` — a machine-readable result, JSON-friendly like the
  rest of aptdata's outputs.

Design goals
------------
* **Single source of truth** — one registry, many consumers.
* **Adapter per backend** — each backend's quirks are isolated in one class.
* **No global state** — specs are passed in explicitly at construction.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Declarative spec — the single source of truth
# ---------------------------------------------------------------------------


class AgentSpec(BaseModel):
    """Declarative description of a single agent backend.

    Loaded from ``agents.yaml``. Carries enough metadata for the registry to
    route to it and for an adapter to reach it, without any consumer needing
    to know how the backend works internally.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    type: str  # adapter kind: openclaw | opencode | claude_code | http
    location: str = "local"  # local | vps
    enabled: bool = True
    role: str = "worker"
    handle: str | None = None  # Telegram handle, if any
    model: str | None = None
    capabilities: list[str] = Field(default_factory=list)

    # Transport (optional — only some adapters use these)
    host: str | None = None
    port: int | None = None
    endpoint: str | None = None
    timeout_ms: int = 30000
    weight: int = 5

    # OpenClaw runtime — name of the container backing this agent, when the
    # adapter reaches the backend through docker compose. Free for other
    # adapters to repurpose; ``None`` means "no container mapping".
    container: str | None = None

    # Free-form, adapter-specific bucket. Kept narrow on purpose: known fields
    # stay first-class above so ``extra="forbid"`` still catches typos, while
    # ``metadata`` holds the long tail that does not deserve its own column.
    metadata: dict[str, Any] | None = None

    note: str = ""

    @property
    def base_url(self) -> str | None:
        """HTTP base URL for adapters that speak over the network."""
        if self.host and self.port:
            return f"http://{self.host}:{self.port}"
        return None


# ---------------------------------------------------------------------------
# Status + response value objects
# ---------------------------------------------------------------------------


class AgentHealth(str, Enum):
    """Coarse liveness of a backend."""

    UP = "up"
    DOWN = "down"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass
class AgentResponse:
    """Result of sending a prompt to an agent.

    JSON-serialisable so it fits aptdata's machine-readable output contract.
    """

    ok: bool
    agent_id: str
    text: str = ""
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "agent_id": self.agent_id,
            "text": self.text,
            "error": self.error,
            "raw": self.raw,
        }


# ---------------------------------------------------------------------------
# Interface + base
# ---------------------------------------------------------------------------


class IAgent(ABC):
    """Uniform interface every backend adapter implements."""

    @abstractmethod
    def send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        """Send a prompt/instruction and return the backend's reply."""
        raise NotImplementedError

    @abstractmethod
    def health(self) -> AgentHealth:
        """Report coarse liveness without side effects on the conversation."""
        raise NotImplementedError


class BaseAgent(IAgent):
    """Common behaviour shared by adapters; holds the declarative spec."""

    #: adapter kind this class handles; subclasses override.
    type: str = "base"

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def capabilities(self) -> list[str]:
        return self.spec.capabilities

    def supports(self, capability: str) -> bool:
        return capability in self.spec.capabilities

    def health(self) -> AgentHealth:
        if not self.spec.enabled:
            return AgentHealth.DISABLED
        return AgentHealth.UNKNOWN

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{self.__class__.__name__} id={self.spec.id!r} type={self.type!r}>"


def observed_send(agent: IAgent, prompt: str, **kwargs: Any) -> AgentResponse:
    """``agent.send`` com traço de observabilidade (dispatch/response + latência).

    Ponto único de emissão para toda superfície que despacha (CLI, ProjectRunner,
    MCP): mantém a fonte de eventos uma só. Best-effort — o Observer nunca
    levanta, e o send acontece mesmo se a emissão falhar.
    """
    import time  # noqa: PLC0415

    from aptdata.observability import Observer  # noqa: PLC0415

    obs = Observer.get()
    agent_id = getattr(agent, "id", None)
    obs.emit("agent.dispatch", {"prompt_chars": len(prompt)}, agent_id=agent_id)
    started = time.perf_counter()
    response = agent.send(prompt, **kwargs)
    obs.emit(
        "agent.response",
        {
            "ok": response.ok,
            "error": response.error,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "text_chars": len(response.text or ""),
        },
        agent_id=agent_id,
    )
    return response
