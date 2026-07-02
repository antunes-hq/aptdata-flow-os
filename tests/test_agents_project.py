"""Tests for aptdata.agents.project — Project, ProjectRunner, scaffolding."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.agents import (
    Project,
    ProjectRunner,
    Router,
    Task,
    scaffold_project,
)
from aptdata.agents.base import AgentResponse

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
    """
)


@pytest.fixture()
def router(tmp_path: Path) -> Router:
    path = tmp_path / "agents.yaml"
    path.write_text(AGENTS_YAML, encoding="utf-8")
    return Router.from_yaml(path)


@pytest.fixture(autouse=True)
def _stub_send(monkeypatch):
    """Make every agent reply deterministically without network."""

    def _send(self, prompt, **kwargs):
        return AgentResponse(ok=True, agent_id=self.id, text=f"done:{prompt[:10]}")

    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(OpenClawAgent, "send", _send)


# ---------------------------------------------------------------------------
# Project model
# ---------------------------------------------------------------------------


class TestProject:
    def test_roundtrip_yaml(self, tmp_path: Path):
        project = scaffold_project("meuapp")
        path = tmp_path / "meuapp.project.yaml"
        project.to_yaml(path)
        loaded = Project.from_yaml(path)
        assert loaded.name == "meuapp"
        assert [t.id for t in loaded.tasks] == [
            "planejar", "backend", "frontend", "deploy",
        ]

    def test_scaffold_has_dependencies(self):
        project = scaffold_project("x")
        deploy = next(t for t in project.tasks if t.id == "deploy")
        assert deploy.depends_on == ["backend", "frontend"]


# ---------------------------------------------------------------------------
# Routing of tasks (plan)
# ---------------------------------------------------------------------------


class TestPlan:
    def test_capability_routing(self, router: Router):
        project = Project(
            name="p",
            tasks=[
                Task(id="a", prompt="faz o backend", capability="backend"),
                Task(id="b", prompt="faz a tela", capability="frontend"),
            ],
        )
        plan = ProjectRunner(project, router).plan()
        assert plan[0].agent_id == "maresia" and plan[0].mode == "capability"
        assert plan[1].agent_id == "ondina"

    def test_explicit_agent_wins(self, router: Router):
        project = Project(
            name="p",
            tasks=[Task(id="a", prompt="qualquer", agent="zeca",
                        capability="frontend")],
        )
        plan = ProjectRunner(project, router).plan()
        assert plan[0].agent_id == "zeca" and plan[0].mode == "explicit"

    def test_skill_fallback_when_no_capability(self, router: Router):
        project = Project(name="p", tasks=[Task(id="a", prompt="bom dia pessoal")])
        plan = ProjectRunner(project, router).plan()
        assert plan[0].agent_id is not None  # default/skill picks something


# ---------------------------------------------------------------------------
# Execution (run)
# ---------------------------------------------------------------------------


class TestRun:
    def test_run_all_ok(self, router: Router):
        project = Project(
            name="p",
            tasks=[
                Task(id="a", prompt="backend", capability="backend"),
                Task(id="b", prompt="frontend", capability="frontend"),
            ],
        )
        results = ProjectRunner(project, router).run()
        assert all(r.ok for r in results)
        assert results[0].text.startswith("done:")

    def test_dependency_skipped_when_upstream_missing(self, router: Router):
        project = Project(
            name="p",
            tasks=[
                Task(id="a", prompt="x", agent="naoexiste"),
                Task(id="b", prompt="y", capability="backend", depends_on=["a"]),
            ],
        )
        results = ProjectRunner(project, router).run()
        assert results[0].ok is False  # unroutable agent
        assert results[1].skipped is True
        assert "dependency" in (results[1].error or "")

    def test_result_to_dict_keeps_text(self, router: Router):
        # o output da task é o produto do run — precisa estar no JSON
        project = Project(
            name="p", tasks=[Task(id="a", prompt="backend", capability="backend")]
        )
        results = ProjectRunner(project, router).run()
        d = results[0].to_dict()
        assert d["text"].startswith("done:")
