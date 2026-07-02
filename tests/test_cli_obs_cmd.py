"""CLI tests for ``aptdata obs`` (obs_cmd.py) — summary/tail do traço.

Segue o padrão dos demais test_cli_*: CliRunner + stubs, nunca rede.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aptdata.agents.base import AgentResponse
from aptdata.cli.app import app
from aptdata.observability import Observer

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
    skills:
      - name: frontend
        keywords: [frontend]
        backend: zeca
    """
)


@pytest.fixture()
def obs_db(tmp_path: Path, monkeypatch) -> Path:
    db = tmp_path / "events.db"
    monkeypatch.setenv("APTDATA_OBS_DB", str(db))
    monkeypatch.delenv("APTDATA_OBS_DISABLED", raising=False)
    Observer.reset()
    yield db
    Observer.reset()


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
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


class TestSummary:
    def test_empty_store_json(self, obs_db):
        r = runner.invoke(app, ["obs", "summary", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["available"] is True
        assert data["total_events"] == 0

    def test_text_mode(self, obs_db):
        r = runner.invoke(app, ["obs", "summary"])
        assert r.exit_code == 0
        assert "events" in r.stdout.lower()


class TestTail:
    def test_empty_json(self, obs_db):
        r = runner.invoke(app, ["obs", "tail", "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data == {"events": [], "count": 0}

    def test_dispatch_leaves_correlated_trace(self, obs_db, agents_file):
        """E2E: um dispatch gera decisão+dispatch+response com o MESMO run_id."""
        r = runner.invoke(
            app, ["agents", "dispatch", "frontend", "--file", agents_file, "--json"]
        )
        assert r.exit_code == 0

        r = runner.invoke(app, ["obs", "tail", "--json"])
        assert r.exit_code == 0
        events = json.loads(r.stdout)["events"]
        kinds = {e["kind"] for e in events}
        assert {"routing.decision", "agent.dispatch", "agent.response"} <= kinds
        run_ids = {e["run_id"] for e in events if e["kind"] != "app.started"}
        assert len(run_ids) == 1 and None not in run_ids

    def test_kind_filter_and_limit(self, obs_db):
        obs = Observer.get()
        for i in range(5):
            obs.emit("a", {"i": i})
        obs.emit("b", {})
        r = runner.invoke(app, ["obs", "tail", "--kind", "a", "-n", "2", "--json"])
        data = json.loads(r.stdout)
        assert data["count"] == 2
        assert all(e["kind"] == "a" for e in data["events"])

    def test_text_mode(self, obs_db):
        Observer.get().emit("routing.decision", {"mode": "skill"}, agent_id="zeca")
        r = runner.invoke(app, ["obs", "tail"])
        assert r.exit_code == 0
        assert "routing.decision" in r.stdout
