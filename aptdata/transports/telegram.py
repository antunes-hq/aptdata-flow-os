"""Transporte Telegram fino — relay de mensagens/botões para o engine.

Fase 2 do docs/plans/telegram-orchestration.md: texto → ``engine.handle``;
clique em botão inline → ``engine.confirm``; o card é renderizado direto do
:class:`~aptdata.agents.conversation.Turn`. Zero lógica de negócio aqui.

Usa a Bot API via HTTP long-polling (``requests``, import lazy — mesmo padrão
do adapter OpenClaw), sem dependência nova. O token NUNCA sai de variável de
ambiente (:class:`~aptdata.config.secrets.SecretManager` o registra para
mascaramento na telemetria).
"""

from __future__ import annotations

import logging
from typing import Any

from aptdata.agents.conversation import ConversationEngine, Turn

logger = logging.getLogger(__name__)

DEFAULT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
API_BASE = "https://api.telegram.org"


def render_turn(turn: Turn) -> dict[str, Any]:
    """Converte um ``Turn`` no payload de ``sendMessage`` (texto + botões).

    Confirmações viram inline keyboard: ✅ confirma a decisão pendente;
    um botão por candidato permite trocar o agente (``mode=override``).
    """
    payload: dict[str, Any] = {"text": turn.text}
    if turn.type == "needs_confirmation" and turn.decision_id:
        rows = [[{
            "text": "✅ Confirmar",
            "callback_data": f"confirm:{turn.decision_id}",
        }]]
        alternates = [
            {"text": f"→ {agent}", "callback_data":
                f"choose:{turn.decision_id}:{agent}"}
            for agent in turn.candidates
            if turn.decision is None or agent != turn.decision.agent_id
        ]
        if alternates:
            rows.append(alternates)
        payload["reply_markup"] = {"inline_keyboard": rows}
    return payload


class TelegramTransport:
    """Bot fino: getUpdates → engine → sendMessage. Sessão = chat_id."""

    def __init__(
        self,
        engine: ConversationEngine,
        token: str | None = None,
        *,
        token_env: str = DEFAULT_TOKEN_ENV,
        api_base: str = API_BASE,
    ):
        if token is None:
            from aptdata.config.secrets import SecretManager  # noqa: PLC0415

            try:
                token = SecretManager(load_dotenv_file=False).get(token_env)
            except KeyError:
                raise ValueError(
                    f"Telegram token ausente: exporte {token_env} "
                    "(rode `aptdata setup` para o passo a passo)."
                ) from None
        self.engine = engine
        self.token = token
        self.api_base = api_base

    # -- Bot API ---------------------------------------------------------------

    def _api(self, method: str, **params: Any) -> dict[str, Any]:
        import requests  # noqa: PLC0415 - lazy, mesmo padrão do OpenClawAgent

        resp = requests.post(
            f"{self.api_base}/bot{self.token}/{method}", json=params, timeout=35
        )
        return resp.json()

    # -- updates -----------------------------------------------------------------

    def handle_update(self, update: dict[str, Any]) -> dict[str, Any] | None:
        """Processa um update do Telegram; devolve o payload respondido."""
        callback = update.get("callback_query")
        if callback and callback.get("data"):
            chat_id = callback["message"]["chat"]["id"]
            turn = self._resolve_callback(chat_id, callback["data"])
            try:
                self._api("answerCallbackQuery", callback_query_id=callback["id"])
            except Exception:  # noqa: BLE001 - ack é cosmético
                pass
        else:
            message = update.get("message") or {}
            text = message.get("text")
            if not text:
                return None
            chat_id = message["chat"]["id"]
            turn = self.engine.handle(self._session(chat_id), text)

        payload = render_turn(turn)
        self._api("sendMessage", chat_id=chat_id, **payload)
        return payload

    def run_polling(self, poll_timeout: int = 25) -> None:  # pragma: no cover
        """Loop de long-polling (bloqueante) — `aptdata telegram` usa isto."""
        offset = None
        logger.info("telegram transport up (long-polling)")
        while True:
            resp = self._api(
                "getUpdates",
                timeout=poll_timeout,
                **({"offset": offset} if offset else {}),
            )
            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                try:
                    self.handle_update(update)
                except Exception:  # noqa: BLE001 - um update ruim não derruba o bot
                    logger.exception("update falhou")

    # -- internos ------------------------------------------------------------------

    @staticmethod
    def _session(chat_id: Any) -> str:
        return f"tg-{chat_id}"

    def _resolve_callback(self, chat_id: Any, data: str) -> Turn:
        session = self._session(chat_id)
        if data.startswith("confirm:"):
            return self.engine.confirm(session, data.split(":", 1)[1])
        if data.startswith("choose:"):
            _, decision_id, agent = data.split(":", 2)
            return self.engine.confirm(session, decision_id, choice=agent)
        return Turn(type="reply", text=f"Ação desconhecida: {data}")
