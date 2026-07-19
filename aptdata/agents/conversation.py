"""ConversationEngine — cérebro de conversa/orquestração (headless).

Fases 0-1 do docs/plans/telegram-orchestration.md: transforma uma mensagem
solta numa decisão de roteamento **transparente**, com confirmação quando faz
sentido, contexto multi-turno e guardrails — reusando o :class:`Router`.

Regra de ouro: nenhuma decisão de rota, threshold ou estado de conversa vive
no transporte (Telegram/CLI/MCP são clientes finos deste engine).

Política de decisão (thresholds no bloco ``routing:`` do agents.yaml):

===============================  =====================
Situação (RouteDecision)         Ação
===============================  =====================
capability guardada (deploy/…)   NEEDS_CONFIRMATION (sempre, ignora confiança)
prefix / explicit / followup     dispatch direto
skill com conf >= dispatch_above dispatch direto
skill médio ou llm               NEEDS_CONFIRMATION
default / none                   NEEDS_CLARIFICATION
===============================  =====================
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from aptdata.agents.base import AgentResponse, observed_send
from aptdata.agents.router import RouteDecision, Router, _normalize
from aptdata.core.state import StateBackend

SESSIONS_ENV = "APTDATA_SESSIONS_DIR"
DEFAULT_SESSIONS_DIR = "~/.aptdata/sessions"

#: follow-ups que reusam o último agente da sessão sem re-rotear
_FOLLOWUP_PHRASES = frozenset(
    {
        "continua",
        "continue",
        "segue",
        "e agora",
        "de novo",
        "manda de novo",
        "pro mesmo",
        "mesmo",
    }
)


# ---------------------------------------------------------------------------
# Contratos (Fase 0)
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    """Resultado de um turno de conversa — o que o transporte renderiza."""

    type: str  # dispatched | needs_confirmation | needs_clarification | reply
    text: str
    decision: RouteDecision | None = None
    response: AgentResponse | None = None
    candidates: list[str] = field(default_factory=list)
    decision_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "text": self.text,
            "decision": self.decision.to_dict() if self.decision else None,
            "response": self.response.to_dict() if self.response else None,
            "candidates": self.candidates,
            "decision_id": self.decision_id,
        }


class DecisionPolicy(BaseModel):
    """Thresholds e guardrails — configuráveis no agents.yaml, não no código."""

    dispatch_above: float = 0.75
    guarded_capabilities: list[str] = Field(
        default_factory=lambda: ["deploy", "ssh", "docker", "ops"]
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> DecisionPolicy:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls(**(raw.get("routing") or {}))

    def decide(self, decision: RouteDecision, router: Router) -> str:
        """Classifica a decisão: ``dispatch`` | ``confirm`` | ``clarify``."""
        if decision.agent_id is None or decision.mode in ("default", "none"):
            return "clarify"
        spec = router.registry.spec(decision.agent_id)
        if set(spec.capabilities) & set(self.guarded_capabilities):
            return "confirm"  # guardrail: destrutivo confirma SEMPRE
        if decision.mode in ("prefix", "explicit", "followup", "override"):
            return "dispatch"
        if decision.mode == "skill" and decision.confidence >= self.dispatch_above:
            return "dispatch"
        return "confirm"  # skill médio, llm


class SessionStore:
    """Estado multi-turno por sessão, persistido em JSON (StateBackend)."""

    def __init__(self, base_dir: str | Path | None = None):
        directory = base_dir or os.getenv(SESSIONS_ENV) or DEFAULT_SESSIONS_DIR
        self._backend = StateBackend(Path(directory).expanduser())

    def get(self, session_id: str) -> dict[str, Any]:
        try:
            return self._backend.load(session_id)
        except FileNotFoundError:
            return {"last_agent": None, "pending": {}}

    def put(self, session_id: str, state: dict[str, Any]) -> None:
        self._backend.save(session_id, state)


# ---------------------------------------------------------------------------
# Engine (Fase 1)
# ---------------------------------------------------------------------------


class ConversationEngine:
    """Conversa → decisão → (confirmação) → dispatch, com traço completo."""

    def __init__(
        self,
        router: Router,
        policy: DecisionPolicy | None = None,
        store: SessionStore | None = None,
    ):
        self.router = router
        self.policy = policy or DecisionPolicy()
        self.store = store or SessionStore()

    @classmethod
    def from_yaml(cls, path: str | Path, *, llm=None) -> ConversationEngine:
        return cls(
            Router.from_yaml(path, llm=llm), policy=DecisionPolicy.from_yaml(path)
        )

    # -- turnos ---------------------------------------------------------------

    def handle(self, session_id: str, text: str) -> Turn:
        """Um turno de conversa: decide, confirma ou esclarece."""
        session = self.store.get(session_id)

        decision = self._followup_decision(session, text)
        if decision is None:
            decision = self.router.route(text)

        action = self.policy.decide(decision, self.router)
        if action == "dispatch":
            return self._dispatch(session_id, session, decision)
        if action == "confirm":
            return self._ask_confirmation(session_id, session, decision)
        return Turn(
            type="needs_clarification",
            text=(
                "Não achei um destino claro para isso — qual área"
                " (frontend/deploy/…) ou qual agente devo usar?"
            ),
            decision=decision,
            candidates=self._candidates(),
        )

    def confirm(
        self, session_id: str, decision_id: str, choice: str | None = None
    ) -> Turn:
        """Resolve uma confirmação pendente (aprova ou troca de agente)."""
        session = self.store.get(session_id)
        pending = (session.get("pending") or {}).pop(decision_id, None)
        if pending is None:
            return Turn(
                type="reply",
                text=f"Decisão '{decision_id}' não encontrada (ou expirada).",
            )
        self.store.put(session_id, session)

        if choice and choice != pending["agent_id"]:
            if choice not in self.router.registry or not (
                self.router.registry.spec(choice).enabled
            ):
                return Turn(type="reply", text=f"Agente '{choice}' indisponível.")
            decision = RouteDecision(
                agent_id=choice,
                mode="override",
                text=pending["text"],
                confidence=1.0,
            )
        else:
            decision = RouteDecision(
                agent_id=pending["agent_id"],
                mode=pending["mode"],
                text=pending["text"],
                confidence=pending.get("confidence", 0.0),
                skill=pending.get("skill"),
                matched_keyword=pending.get("matched_keyword"),
            )

        self._emit(
            "permission.resolved",
            {
                "decision_id": decision_id,
                "approved": True,
                "chosen": decision.agent_id,
                "overridden": decision.mode == "override",
            },
            agent_id=decision.agent_id,
        )
        return self._dispatch(session_id, session, decision)

    # -- internos ---------------------------------------------------------------

    def _followup_decision(
        self, session: dict[str, Any], text: str
    ) -> RouteDecision | None:
        if _normalize(text).strip("?!. ") not in _FOLLOWUP_PHRASES:
            return None
        last = session.get("last_agent")
        if (
            last
            and last in self.router.registry
            and self.router.registry.spec(last).enabled
        ):
            return RouteDecision(
                agent_id=last, mode="followup", text=text, confidence=0.9
            )
        return None

    def _candidates(self) -> list[str]:
        return [s.id for s in self.router.registry.specs() if s.enabled]

    def _dispatch(
        self, session_id: str, session: dict[str, Any], decision: RouteDecision
    ) -> Turn:
        from aptdata.observability import Observer  # noqa: PLC0415

        with Observer.get().run_context():
            response = observed_send(
                self.router.registry.get(decision.agent_id), decision.text
            )
        session["last_agent"] = decision.agent_id
        self.store.put(session_id, session)
        prefix = f"[{decision.agent_id}]"
        text = (
            f"{prefix} {response.text}"
            if response.ok
            else (f"{prefix} erro: {response.error}")
        )
        return Turn(type="dispatched", text=text, decision=decision, response=response)

    def _ask_confirmation(
        self, session_id: str, session: dict[str, Any], decision: RouteDecision
    ) -> Turn:
        decision_id = uuid.uuid4().hex[:8]
        session.setdefault("pending", {})[decision_id] = decision.to_dict()
        self.store.put(session_id, session)
        self._emit(
            "permission.requested",
            {"decision_id": decision_id, **decision.to_dict()},
            agent_id=decision.agent_id,
        )
        skill = f" · skill {decision.skill}" if decision.skill else ""
        return Turn(
            type="needs_confirmation",
            text=(
                f"🧭 {decision.agent_id} · {decision.mode}{skill}"
                f" · conf {decision.confidence:.2f} — confirmar, trocar ou editar?"
            ),
            decision=decision,
            candidates=self._candidates(),
            decision_id=decision_id,
        )

    @staticmethod
    def _emit(kind: str, payload: dict[str, Any], *, agent_id: str | None) -> None:
        try:  # observabilidade é best-effort
            from aptdata.observability import Observer  # noqa: PLC0415

            Observer.get().emit(kind, payload, agent_id=agent_id)
        except Exception:  # noqa: BLE001 - façade quebrado não pode vazar
            pass
