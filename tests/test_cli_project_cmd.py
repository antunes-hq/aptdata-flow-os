"""CLI tests for ``aptdata project`` sub-commands (project_cmd.py).

Covers init / plan / run and the project-file error path. Agent ``.send`` is
stubbed so ``run`` never touches the network.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aptdata.agents import scaffold_project
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
        capabilities: [planning, chat]
        weight: 10
        enabled: true
      maresia:
        name: Maresia
        type: openclaw
        capabilities: [backend]
        weight: 7
        enabled: true
      ondina:
        name: Ondina
        type: openclaw
        capabilities: [frontend]
        weight: 8
        enabled: true
      hermez:
        name: Hermez
        type: openclaw
        capabilities: [deploy]
        weight: 6
        enabled: true
    """
)


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
    path = tmp_path / "agents.yaml"
    path.write_text(AGENTS_YAML, encoding="utf-8")
    return str(path)


@pytest.fixture()
def project_file(tmp_path: Path) -> str:
    path = tmp_path / "demo.project.yaml"
    scaffold_project("demo").to_yaml(path)
    return str(path)


@pytest.fixture(autouse=True)
def _stub_send(monkeypatch):
    def _send(self, prompt, **kwargs):
        return AgentResponse(ok=True, agent_id=self.id, text=f"ok:{prompt[:8]}")

    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(OpenClawAgent, "send", _send)


class TestInit:
    def test_creates_file_json(self, tmp_path):
        out = tmp_path / "novo.project.yaml"
        r = runner.invoke(app, ["project", "init", "novo", "--out", str(out), "--json"])
        assert r.exit_code == 0
        assert out.exists()
        data = json.loads(r.stdout)
        assert data["created"] == str(out) and data["tasks"] >= 1

    def test_creates_file_text(self, tmp_path):
        out = tmp_path / "novo2.project.yaml"
        r = runner.invoke(app, ["project", "init", "novo2", "--out", str(out)])
        assert r.exit_code == 0
        assert out.exists() and "novo2" in r.stdout

    def test_refuses_overwrite(self, tmp_path):
        out = tmp_path / "existe.project.yaml"
        out.write_text("name: existe\n", encoding="utf-8")
        r = runner.invoke(app, ["project", "init", "existe", "--out", str(out)])
        assert r.exit_code == 1


class TestPlan:
    def test_json(self, project_file, agents_file):
        r = runner.invoke(
            app,
            ["project", "plan", project_file, "--file", agents_file, "--json"],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["project"] == "demo" and len(data["plan"]) >= 1
        # PR3 — plan expõe mode=project + dry_run=True (plan é sempre plan-only)
        assert data["mode"] == "project"
        assert data["dry_run"] is True

    def test_mode_override_to_oneshot(self, project_file, agents_file):
        r = runner.invoke(
            app,
            [
                "project",
                "plan",
                project_file,
                "--file",
                agents_file,
                "--json",
                "--mode",
                "oneshot",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["mode"] == "oneshot"

    def test_text(self, project_file, agents_file):
        r = runner.invoke(app, ["project", "plan", project_file, "--file", agents_file])
        assert r.exit_code == 0
        assert "demo" in r.stdout

    def test_missing_project_errors(self, tmp_path, agents_file):
        r = runner.invoke(
            app,
            ["project", "plan", str(tmp_path / "nope.yaml"), "--file", agents_file],
        )
        assert r.exit_code != 0


class TestRun:
    def test_all_ok_json(self, project_file, agents_file):
        r = runner.invoke(
            app,
            ["project", "run", project_file, "--file", agents_file, "--json"],
        )
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["ok"] == data["total"] and data["total"] >= 1
        # o texto de resposta de cada task faz parte do contrato JSON
        assert all("text" in item for item in data["results"])
        assert any(item["text"] for item in data["results"])
        # PR3 — run expõe mode=project no JSON
        assert data["mode"] == "project"

    def test_mode_override_to_orchestrated(self, project_file, agents_file):
        r = runner.invoke(
            app,
            [
                "project",
                "run",
                project_file,
                "--file",
                agents_file,
                "--json",
                "--mode",
                "orchestrated",
            ],
        )
        assert r.exit_code == 0
        assert json.loads(r.stdout)["mode"] == "orchestrated"

    def test_dry_run_aliases_plan(self, project_file, agents_file):
        """--dry-run em run == plan: roteia tasks sem despachar nenhum send."""
        r = runner.invoke(
            app,
            [
                "project",
                "run",
                project_file,
                "--file",
                agents_file,
                "--dry-run",
                "--json",
            ],
        )
        assert r.exit_code == 0, r.stdout
        data = json.loads(r.stdout)
        assert data["mode"] == "project"
        assert data["dry_run"] is True
        assert "plan" in data
        assert len(data["plan"]) >= 1
        # nenhum "results" (não despachou)
        assert "results" not in data
        # cada task do plan tem task_id + agent_id + mode
        for item in data["plan"]:
            assert {"task_id", "agent_id", "mode"} <= set(item)

    def test_dry_run_text_mode(self, project_file, agents_file):
        r = runner.invoke(
            app,
            ["project", "run", project_file, "--file", agents_file, "--dry-run"],
        )
        assert r.exit_code == 0
        assert "dry-run" in r.stdout
        assert "demo" in r.stdout

    def test_text(self, project_file, agents_file):
        r = runner.invoke(app, ["project", "run", project_file, "--file", agents_file])
        assert r.exit_code == 0
        assert "demo" in r.stdout

    def test_failure_exits_1(self, project_file, agents_file, monkeypatch):
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(
                ok=False, agent_id=self.id, error="boom"
            ),
        )
        r = runner.invoke(app, ["project", "run", project_file, "--file", agents_file])
        assert r.exit_code == 1
