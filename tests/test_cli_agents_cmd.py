"""CLI tests for ``aptdata agents`` sub-commands (agents_cmd.py).

Covers list / send / route / dispatch / resolve and the agents-file resolution
error path. Agent ``.send`` is stubbed so nothing hits the network.
"""

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
        capabilities: [chat, orchestration]
        weight: 10
        enabled: true
      ondina:
        name: Ondina
        type: openclaw
        capabilities: [frontend]
        weight: 8
        enabled: true
      holt:
        name: Holt
        type: openclaw
        capabilities: [monitoria]
        weight: 6
        enabled: false
    skills:
      - name: frontend
        keywords: [frontend, tela, pagina]
        backend: ondina
        fallback: [zeca]
    """
)


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
    path = tmp_path / "agents.yaml"
    path.write_text(AGENTS_YAML, encoding="utf-8")
    return str(path)


@pytest.fixture(autouse=True)
def _stub_send(monkeypatch):
    """Every OpenClaw agent replies deterministically, no network."""

    def _send(self, prompt, **kwargs):
        return AgentResponse(ok=True, agent_id=self.id, text=f"reply:{prompt}")

    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(OpenClawAgent, "send", _send)


def _fail_send(monkeypatch):
    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(
        OpenClawAgent,
        "send",
        lambda self, p, **k: AgentResponse(ok=False, agent_id=self.id, error="boom"),
    )


class TestList:
    def test_json_lists_all(self, agents_file):
        r = runner.invoke(app, ["agents", "list", "--file", agents_file, "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["count"] == 3
        assert {a["id"] for a in data["agents"]} == {"zeca", "ondina", "holt"}

    def test_enabled_only_hides_disabled(self, agents_file):
        r = runner.invoke(
            app, ["agents", "list", "--file", agents_file, "--enabled", "--json"]
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["count"] == 2

    def test_text_mode(self, agents_file):
        r = runner.invoke(app, ["agents", "list", "--file", agents_file])
        assert r.exit_code == 0
        assert "zeca" in r.stdout

    def test_missing_file_errors(self, tmp_path):
        r = runner.invoke(
            app, ["agents", "list", "--file", str(tmp_path / "nope.yaml")]
        )
        assert r.exit_code != 0


class TestSend:
    def test_success_text(self, agents_file):
        r = runner.invoke(app, ["agents", "send", "zeca", "oi", "--file", agents_file])
        assert r.exit_code == 0
        assert "reply:oi" in r.stdout

    def test_success_json(self, agents_file):
        r = runner.invoke(
            app, ["agents", "send", "zeca", "oi", "--file", agents_file, "--json"]
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["ok"] is True
        # PR3 — ExecutionMode exposto no JSON (oneshot é o default natural de send)
        assert data["mode"] == "oneshot"

    def test_mode_override_to_orchestrated(self, agents_file):
        """--mode explícito vence o default do comando."""
        r = runner.invoke(
            app,
            [
                "agents",
                "send",
                "zeca",
                "oi",
                "--file",
                agents_file,
                "--json",
                "--mode",
                "orchestrated",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["mode"] == "orchestrated"

    def test_dry_run_does_not_send(self, agents_file):
        r = runner.invoke(
            app,
            [
                "agents",
                "send",
                "zeca",
                "oi",
                "--file",
                agents_file,
                "--dry-run",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.stdout
        data = json.loads(r.stdout)
        assert data["mode"] == "oneshot"
        assert data["dry_run"] is True
        assert data["agent_id"] == "zeca"
        assert data["prompt"] == "oi"
        assert data["would_send"] is True
        # nada despachado: sem `text` (resposta), `raw`, `error` de AgentResponse.
        assert "raw" not in data
        assert data.get("error") in (None,)
        assert "text" not in data or data.get("text") in ("", None)

    def test_dry_run_text_mode(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "send", "zeca", "oi", "--file", agents_file, "--dry-run"],
        )
        assert r.exit_code == 0
        assert "dry-run" in r.stdout
        assert "zeca" in r.stdout

    def test_dry_run_unknown_agent_exits_1(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "send", "ninguem", "oi", "--file", agents_file, "--dry-run"],
        )
        assert r.exit_code == 1

    def test_invalid_mode_exits_nonzero(self, agents_file):
        r = runner.invoke(
            app,
            [
                "agents",
                "send",
                "zeca",
                "oi",
                "--file",
                agents_file,
                "--mode",
                "bogus",
            ],
        )
        assert r.exit_code != 0

    def test_json_exposes_raw_diagnostics(self, agents_file, monkeypatch):
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(
                ok=False,
                agent_id=self.id,
                error="HTTP 502",
                raw={"status": 502, "body": "bad gateway"},
            ),
        )
        r = runner.invoke(
            app, ["agents", "send", "zeca", "oi", "--file", agents_file, "--json"]
        )
        assert r.exit_code == 1
        data = json.loads(r.stdout)
        assert data["raw"] == {"status": 502, "body": "bad gateway"}

    def test_unknown_agent_exits_1(self, agents_file):
        r = runner.invoke(
            app, ["agents", "send", "ninguem", "oi", "--file", agents_file]
        )
        assert r.exit_code == 1

    def test_send_failure_exits_1(self, agents_file, monkeypatch):
        _fail_send(monkeypatch)
        r = runner.invoke(app, ["agents", "send", "zeca", "oi", "--file", agents_file])
        assert r.exit_code == 1


class TestRoute:
    def test_json_routes_to_skill_backend(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "route", "mexer no frontend", "--file", agents_file, "--json"],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert "ondina" in r.stdout
        # PR3 — route expõe mode=orchestrated no JSON
        assert data["mode"] == "orchestrated"

    def test_mode_override_to_oneshot(self, agents_file):
        r = runner.invoke(
            app,
            [
                "agents",
                "route",
                "mexer no frontend",
                "--file",
                agents_file,
                "--json",
                "--mode",
                "oneshot",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["mode"] == "oneshot"

    def test_text_mode(self, agents_file):
        r = runner.invoke(
            app, ["agents", "route", "bom dia pessoal", "--file", agents_file]
        )
        assert r.exit_code == 0


class TestDispatch:
    def test_success_json(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "dispatch", "tela nova", "--file", agents_file, "--json"],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["routed_to"] == "ondina" and data["ok"] is True
        # PR3 — dispatch expõe mode=orchestrated
        assert data["mode"] == "orchestrated"
        # routing_mode preserva o RouteDecision.mode (skill/prefix/...)
        assert data["routing_mode"] == "skill"

    def test_mode_override_to_project(self, agents_file):
        r = runner.invoke(
            app,
            [
                "agents",
                "dispatch",
                "tela nova",
                "--file",
                agents_file,
                "--json",
                "--mode",
                "project",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["mode"] == "project"

    def test_dry_run_does_not_send(self, agents_file):
        r = runner.invoke(
            app,
            [
                "agents",
                "dispatch",
                "tela nova",
                "--file",
                agents_file,
                "--dry-run",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.stdout
        data = json.loads(r.stdout)
        assert data["mode"] == "orchestrated"
        assert data["routing_mode"] == "skill"
        assert data["dry_run"] is True
        assert data["agent_id"] == "ondina"
        assert data["would_send"] is True
        # nada foi despachado: não há `raw`, `error`, `ok` de AgentResponse.
        assert "raw" not in data
        assert data.get("error") in (None,)
        assert data["ok"] is True

    def test_dry_run_text_mode(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "dispatch", "tela nova", "--file", agents_file, "--dry-run"],
        )
        assert r.exit_code == 0
        assert "dry-run" in r.stdout
        assert "ondina" in r.stdout

    def test_dry_run_no_agent_exits_1(self, agents_file):
        # Um agents.yaml sem nenhum agent habilitado → route devolve agent_id=None.
        from pathlib import Path

        empty_path = Path(agents_file).parent / "empty.yaml"
        empty_path.write_text("agents: {}\nskills: []\n", encoding="utf-8")
        r = runner.invoke(
            app,
            [
                "agents",
                "dispatch",
                "tela nova",
                "--file",
                str(empty_path),
                "--dry-run",
                "--json",
            ],
        )
        assert r.exit_code == 1
        data = json.loads(r.stdout)
        assert data["dry_run"] is True
        assert data["ok"] is False

    def test_text_mode(self, agents_file):
        r = runner.invoke(
            app, ["agents", "dispatch", "tela nova", "--file", agents_file]
        )
        assert r.exit_code == 0

    def test_failure_exits_1(self, agents_file, monkeypatch):
        _fail_send(monkeypatch)
        r = runner.invoke(
            app, ["agents", "dispatch", "tela nova", "--file", agents_file]
        )
        assert r.exit_code == 1


class TestResolve:
    def test_found_text(self, agents_file):
        r = runner.invoke(app, ["agents", "resolve", "frontend", "--file", agents_file])
        assert r.exit_code == 0
        assert "ondina" in r.stdout

    def test_found_json(self, agents_file):
        r = runner.invoke(
            app, ["agents", "resolve", "frontend", "--file", agents_file, "--json"]
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["agent"] == "ondina"

    def test_not_found_exits_1(self, agents_file):
        r = runner.invoke(
            app,
            ["agents", "resolve", "inexistente", "--file", agents_file, "--json"],
        )
        assert r.exit_code == 1
        assert json.loads(r.stdout)["agent"] is None
