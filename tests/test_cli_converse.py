"""CLI + MCP tests for ``converse`` — transportes finos do ConversationEngine."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aptdata.agents.base import AgentResponse
from aptdata.cli.app import app

runner = CliRunner()

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
def agents_file(tmp_path: Path, monkeypatch) -> str:
    monkeypatch.setenv("APTDATA_SESSIONS_DIR", str(tmp_path / "sessions"))
    p = tmp_path / "agents.yaml"
    p.write_text(AGENTS_YAML, encoding="utf-8")
    return str(p)


@pytest.fixture(autouse=True)
def _stub_send(monkeypatch):
    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(
        OpenClawAgent,
        "send",
        lambda self, p, **k: AgentResponse(ok=True, agent_id=self.id, text=f"re:{p}"),
    )


class TestConverseCli:
    def test_dispatch_json(self, agents_file):
        r = runner.invoke(
            app, ["converse", "mexer no frontend", "-f", agents_file, "--json"]
        )
        assert r.exit_code == 0
        turn = json.loads(r.stdout)
        assert turn["type"] == "dispatched"
        assert turn["decision"]["agent_id"] == "zeca"
        assert turn["response"]["ok"] is True

    def test_guarded_asks_confirmation_then_confirms(self, agents_file):
        r = runner.invoke(
            app, ["converse", "/hermez deploy", "-f", agents_file, "--json"]
        )
        turn = json.loads(r.stdout)
        assert turn["type"] == "needs_confirmation"
        decision_id = turn["decision_id"]

        r2 = runner.invoke(
            app,
            ["converse", "--confirm", decision_id, "-f", agents_file, "--json"],
        )
        assert r2.exit_code == 0
        done = json.loads(r2.stdout)
        assert done["type"] == "dispatched"
        assert done["decision"]["agent_id"] == "hermez"

    def test_yes_auto_confirms(self, agents_file):
        r = runner.invoke(
            app,
            ["converse", "/hermez deploy", "-f", agents_file, "--yes", "--json"],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["type"] == "dispatched"

    def test_text_mode_shows_confirm_hint(self, agents_file):
        r = runner.invoke(app, ["converse", "/hermez deploy", "-f", agents_file])
        assert r.exit_code == 0
        assert "--confirm" in r.stdout

    def test_no_text_and_no_confirm_exits_2(self, agents_file):
        r = runner.invoke(app, ["converse", "-f", agents_file])
        assert r.exit_code == 2

    def test_failed_dispatch_exits_1(self, agents_file, monkeypatch):
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(
                ok=False, agent_id=self.id, error="boom"
            ),
        )
        r = runner.invoke(
            app, ["converse", "mexer no frontend", "-f", agents_file, "--json"]
        )
        assert r.exit_code == 1


class TestConverseMcp:
    def test_converse_and_confirm_tools(self, agents_file, monkeypatch):
        monkeypatch.setenv("APTDATA_AGENTS_FILE", agents_file)
        from aptdata.mcp.server import confirm, converse

        turn = converse("mcp-s1", "/hermez deploy")
        assert turn["type"] == "needs_confirmation"

        done = confirm("mcp-s1", turn["decision_id"])
        assert done["type"] == "dispatched"
        assert done["decision"]["agent_id"] == "hermez"

    def test_converse_tool_degrades_gracefully(self, monkeypatch, tmp_path):
        monkeypatch.setenv("APTDATA_AGENTS_FILE", str(tmp_path / "nope.yaml"))
        from aptdata.mcp.server import converse

        out = converse("s", "oi")
        # arquivo ausente -> erro estruturado, nunca exceção crua
        assert out.get("status") == "error" or out.get("type") == "needs_clarification"
