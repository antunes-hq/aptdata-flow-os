"""Tests for aptdata.transports.telegram — transporte FINO sobre o engine.

Regra de ouro (telegram-orchestration.md §2): o transporte só renderiza
cards/botões e releia o engine — nenhuma decisão de rota, threshold ou
estado de conversa vive aqui. API do Telegram sempre stubada (nunca rede).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.agents.base import AgentResponse
from aptdata.agents.conversation import ConversationEngine
from aptdata.transports.telegram import TelegramTransport, render_turn

AGENTS_YAML = textwrap.dedent(
    """
    agents:
      zeca:
        name: Zeca
        type: openclaw
        role: porta_de_entrada
        capabilities: [chat]
        weight: 10
        enabled: true
      hermez:
        name: Hermez
        type: openclaw
        capabilities: [deploy]
        weight: 7
        enabled: true
    skills:
      - name: frontend
        keywords: [frontend]
        backend: zeca
    routing:
      guarded_capabilities: [deploy]
    """
)


@pytest.fixture()
def engine(tmp_path: Path, monkeypatch) -> ConversationEngine:
    monkeypatch.setenv("APTDATA_SESSIONS_DIR", str(tmp_path / "sessions"))
    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(
        OpenClawAgent,
        "send",
        lambda self, p, **k: AgentResponse(ok=True, agent_id=self.id, text=f"re:{p}"),
    )
    p = tmp_path / "agents.yaml"
    p.write_text(AGENTS_YAML, encoding="utf-8")
    return ConversationEngine.from_yaml(p)


@pytest.fixture()
def transport(engine: ConversationEngine):
    t = TelegramTransport(engine, token="123:abc")
    t.sent = []
    t._api = lambda method, **params: t.sent.append((method, params)) or {"ok": True}
    return t


def _msg(text: str, chat_id: int = 42) -> dict:
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def _callback(data: str, chat_id: int = 42) -> dict:
    return {
        "callback_query": {
            "id": "cb1",
            "data": data,
            "message": {"chat": {"id": chat_id}},
        }
    }


class TestRenderTurn:
    def test_dispatched_is_plain_text(self, engine):
        turn = engine.handle("s", "mexer no frontend")
        payload = render_turn(turn)
        assert payload["text"].startswith("[zeca]")
        assert "reply_markup" not in payload

    def test_confirmation_renders_buttons(self, engine):
        turn = engine.handle("s", "/hermez deploy")
        payload = render_turn(turn)
        assert "🧭" in payload["text"]
        keyboard = payload["reply_markup"]["inline_keyboard"]
        flat = [b for row in keyboard for b in row]
        datas = {b["callback_data"] for b in flat}
        assert f"confirm:{turn.decision_id}" in datas
        assert f"choose:{turn.decision_id}:zeca" in datas


class TestHandleUpdate:
    def test_text_message_dispatches_and_replies(self, transport):
        transport.handle_update(_msg("mexer no frontend"))
        methods = [m for m, _ in transport.sent]
        assert "sendMessage" in methods
        _, params = transport.sent[-1]
        assert params["chat_id"] == 42
        assert params["text"].startswith("[zeca]")

    def test_guarded_message_asks_with_buttons(self, transport):
        transport.handle_update(_msg("/hermez sobe a versao"))
        _, params = transport.sent[-1]
        assert "reply_markup" in params
        assert "confirm:" in str(params["reply_markup"])

    def test_confirm_callback_dispatches(self, transport, engine):
        transport.handle_update(_msg("/hermez sobe a versao"))
        _, ask = transport.sent[-1]
        decision_id = next(
            b["callback_data"].split(":", 1)[1]
            for row in ask["reply_markup"]["inline_keyboard"]
            for b in row
            if b["callback_data"].startswith("confirm:")
        )
        transport.handle_update(_callback(f"confirm:{decision_id}"))
        _, params = transport.sent[-1]
        assert params["text"].startswith("[hermez]")

    def test_choose_callback_overrides_agent(self, transport):
        transport.handle_update(_msg("/hermez sobe a versao"))
        _, ask = transport.sent[-1]
        choose = next(
            b["callback_data"]
            for row in ask["reply_markup"]["inline_keyboard"]
            for b in row
            if b["callback_data"].startswith("choose:")
            and b["callback_data"].endswith(":zeca")
        )
        transport.handle_update(_callback(choose))
        _, params = transport.sent[-1]
        assert params["text"].startswith("[zeca]")

    def test_sessions_follow_chat_id(self, transport):
        transport.handle_update(_msg("mexer no frontend", chat_id=1))
        transport.handle_update(_msg("continua", chat_id=1))
        _, params = transport.sent[-1]
        assert params["text"].startswith("[zeca]")  # followup no mesmo chat
        transport.handle_update(_msg("continua", chat_id=2))
        _, params2 = transport.sent[-1]
        assert "destino claro" in params2["text"]  # chat novo não herda sessão

    def test_ignores_updates_without_text(self, transport):
        assert transport.handle_update({"message": {"chat": {"id": 1}}}) is None
        assert transport.sent == []


class TestTokenResolution:
    def test_missing_token_raises_clear_error(self, engine, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
            TelegramTransport(engine)

    def test_token_from_env_via_secret_manager(self, engine, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "999:xyz")
        t = TelegramTransport(engine)
        assert t.token == "999:xyz"
