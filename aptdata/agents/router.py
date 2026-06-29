"""Router — decides which agent should handle a given prompt.

Ports the three-mode routing of the Telegram plugin into aptdata so the
logic is testable, transport-agnostic and reusable from CLI/MCP:

1. **Prefix** (``/darwin faz X``) — explicit, always wins.
2. **Skill match** — keyword → backend via the ``skills`` table, accent- and
   case-insensitive, best (longest) keyword wins.
3. **LLM** — optional injected callable for fuzzy cases.
4. **Default** — falls back to the entry-point agent.

Disabled targets are skipped in favour of their declared fallbacks.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from aptdata.agents.base import AgentSpec
from aptdata.agents.registry import AgentRegistry

logger = logging.getLogger(__name__)

_PREFIX_RE = re.compile(r"^/(\w+)(?:\s+(.*))?$", re.DOTALL)

#: callable(text, candidates) -> agent_id | None
LLMRouter = Callable[[str, "list[AgentSpec]"], "str | None"]


class Skill(BaseModel):
    """A keyword bucket pointing at a preferred backend (+ fallbacks)."""

    name: str
    keywords: list[str]
    backend: str
    fallback: list[str] = Field(default_factory=list)


@dataclass
class RouteDecision:
    """Outcome of routing a prompt."""

    agent_id: str | None
    mode: str  # prefix | skill | llm | default | none
    text: str
    confidence: float = 0.0
    skill: str | None = None
    matched_keyword: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "mode": self.mode,
            "confidence": round(self.confidence, 3),
            "skill": self.skill,
            "matched_keyword": self.matched_keyword,
            "text": self.text,
        }


def _normalize(text: str) -> str:
    """Lowercase and strip accents so PT-BR keywords match reliably."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


class Router:
    """Routes prompts to agents using prefix / skill / LLM / default."""

    def __init__(
        self,
        registry: AgentRegistry,
        skills: list[Skill] | None = None,
        llm: LLMRouter | None = None,
        default_agent: str | None = None,
    ) -> None:
        self.registry = registry
        self.skills = skills or []
        self.llm = llm
        self._default = default_agent

    # -- construction -------------------------------------------------------

    @classmethod
    def from_yaml(
        cls, path: str | Path, *, llm: LLMRouter | None = None
    ) -> Router:
        path = Path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        registry = AgentRegistry.from_yaml(path)
        skills = [Skill(**s) for s in raw.get("skills", [])]
        return cls(registry, skills=skills, llm=llm)

    # -- default ------------------------------------------------------------

    @property
    def default_agent(self) -> str | None:
        """Entry-point agent: explicit, else 'porta_de_entrada', else top weight."""
        if self._default and self._default in self.registry:
            return self._default
        enabled = [s for s in self.registry.specs() if s.enabled]
        if not enabled:
            return None
        for spec in enabled:
            if spec.role == "porta_de_entrada":
                return spec.id
        return max(enabled, key=lambda s: s.weight).id

    # -- mode 1: prefix -----------------------------------------------------

    def detect_prefix(self, text: str) -> tuple[str, str] | None:
        match = _PREFIX_RE.match(text.strip())
        if not match:
            return None
        agent_id = match.group(1).lower()
        rest = (match.group(2) or "").strip()
        if agent_id in self.registry:
            return agent_id, rest
        return None

    # -- mode 2: skill ------------------------------------------------------

    def _resolve(self, backend: str, fallback: list[str]) -> str | None:
        """First enabled agent among [backend, *fallback]."""
        for candidate in (backend, *fallback):
            if candidate in self.registry and self.registry.spec(candidate).enabled:
                return candidate
        return None

    def match_skill(self, text: str) -> RouteDecision | None:
        normalized = _normalize(text)
        if not normalized:
            return None

        best: RouteDecision | None = None
        for skill in self.skills:
            for keyword in skill.keywords:
                kw = _normalize(keyword)
                if kw and kw in normalized:
                    confidence = min(1.0, len(kw) / len(normalized) + 0.5)
                    if best is None or confidence > best.confidence:
                        target = self._resolve(skill.backend, skill.fallback)
                        if target is None:
                            continue
                        best = RouteDecision(
                            agent_id=target,
                            mode="skill",
                            text=text,
                            confidence=confidence,
                            skill=skill.name,
                            matched_keyword=keyword,
                        )
        return best

    # -- orchestration ------------------------------------------------------

    def route(self, text: str) -> RouteDecision:
        # 1. explicit prefix
        prefix = self.detect_prefix(text)
        if prefix:
            agent_id, rest = prefix
            if self.registry.spec(agent_id).enabled:
                return RouteDecision(
                    agent_id=agent_id, mode="prefix", text=rest, confidence=1.0
                )

        # 2. skill match
        skill = self.match_skill(text)
        if skill:
            return skill

        # 3. LLM fallback (optional)
        if self.llm is not None:
            candidates = [s for s in self.registry.specs() if s.enabled]
            try:
                choice = self.llm(text, candidates)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("LLM router failed: %s", exc)
                choice = None
            if choice and choice in self.registry:
                return RouteDecision(
                    agent_id=choice, mode="llm", text=text, confidence=0.5
                )

        # 4. default
        default = self.default_agent
        if default:
            return RouteDecision(
                agent_id=default, mode="default", text=text, confidence=0.3
            )

        return RouteDecision(agent_id=None, mode="none", text=text)
