"""Tests for aptdata.observability — Observer (façade no-throw) + store SQLite.

Contrato (docs/plans/observability.md):
- best-effort universal: falha de telemetria NUNCA derruba o fluxo;
- kill-switch por env (APTDATA_OBS_DISABLED);
- correlação por run_id ponta-a-ponta (Router → Agent → Task);
- persistência própria (SQLite), sem depender de store externo.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.observability import ObservabilityStore, Observer

AGENTS_YAML = textwrap.dedent(
    """
    agents:
      zeca:
        name: Zeca
        type: openclaw
        role: porta_de_entrada
        capabilities: [chat, planning, backend, frontend]
        weight: 10
        enabled: true
    skills:
      - name: frontend
        keywords: [frontend, tela]
        backend: zeca
    """
)


@pytest.fixture()
def obs_db(tmp_path: Path, monkeypatch) -> Path:
    """Isola o Observer num banco temporário e reseta o singleton."""
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


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class TestStore:
    def test_append_and_tail_roundtrip(self, tmp_path: Path):
        store = ObservabilityStore(tmp_path / "e.db")
        store.append("routing.decision", {"mode": "skill"}, run_id="r1")
        store.append("agent.response", {"ok": True}, run_id="r1", agent_id="zeca")
        events = store.tail(limit=10)
        assert [e["kind"] for e in events] == ["routing.decision", "agent.response"]
        assert events[0]["payload"] == {"mode": "skill"}
        assert events[1]["agent_id"] == "zeca"
        assert all(e["run_id"] == "r1" for e in events)
        store.close()

    def test_tail_filters_kind_and_run_id(self, tmp_path: Path):
        store = ObservabilityStore(tmp_path / "e.db")
        store.append("a", {}, run_id="r1")
        store.append("b", {}, run_id="r2")
        store.append("a", {}, run_id="r2")
        assert len(store.tail(kind="a")) == 2
        assert len(store.tail(run_id="r2")) == 2
        assert len(store.tail(kind="a", run_id="r2")) == 1
        store.close()

    def test_tail_returns_last_n_in_order(self, tmp_path: Path):
        store = ObservabilityStore(tmp_path / "e.db")
        for i in range(10):
            store.append("k", {"i": i})
        events = store.tail(limit=3)
        assert [e["payload"]["i"] for e in events] == [7, 8, 9]
        store.close()

    def test_summary_aggregates(self, tmp_path: Path):
        store = ObservabilityStore(tmp_path / "e.db")
        store.append("routing.decision", {"mode": "skill"})
        store.append("routing.decision", {"mode": "default"})
        store.append("agent.response", {"ok": True, "latency_ms": 100.0})
        store.append("agent.response", {"ok": False, "latency_ms": 300.0})
        s = store.summary()
        assert s["available"] is True
        assert s["total_events"] == 4
        assert s["by_kind"]["routing.decision"] == 2
        assert s["decisions_by_mode"] == {"skill": 1, "default": 1}
        assert s["dispatches"]["total"] == 2
        assert s["dispatches"]["ok"] == 1
        assert s["dispatches"]["error"] == 1
        assert s["dispatches"]["avg_latency_ms"] == pytest.approx(200.0)
        store.close()

    def test_persists_across_instances(self, tmp_path: Path):
        db = tmp_path / "e.db"
        first = ObservabilityStore(db)
        first.append("k", {"x": 1})
        first.close()
        second = ObservabilityStore(db)
        assert second.summary()["total_events"] == 1
        second.close()


# ---------------------------------------------------------------------------
# Observer (façade)
# ---------------------------------------------------------------------------


class TestObserver:
    def test_emit_persists_with_run_context(self, obs_db: Path):
        obs = Observer.get()
        with obs.run_context() as run_id:
            obs.emit("agent.dispatch", {"prompt_chars": 3}, agent_id="zeca")
        events = obs.tail(limit=5)
        assert events[-1]["run_id"] == run_id
        assert events[-1]["agent_id"] == "zeca"

    def test_run_context_reuses_active_run(self, obs_db: Path):
        obs = Observer.get()
        with obs.run_context("run-x") as outer:
            with obs.run_context() as inner:
                assert inner == outer == "run-x"

    def test_kill_switch_disables_emission(self, obs_db: Path, monkeypatch):
        monkeypatch.setenv("APTDATA_OBS_DISABLED", "1")
        Observer.reset()
        obs = Observer.get()
        obs.emit("k", {"x": 1})
        assert obs.tail(limit=5) == []

    def test_emit_never_raises_on_broken_store(self, obs_db: Path):
        class _Broken:
            def append(self, *a, **k):
                raise RuntimeError("disk on fire")

        obs = Observer.get()
        obs._store = _Broken()
        obs.emit("k", {"x": 1})  # não pode levantar

    def test_emit_never_raises_on_unserializable_payload(self, obs_db: Path):
        obs = Observer.get()
        obs.emit("k", {"bad": object()})  # não pode levantar


# ---------------------------------------------------------------------------
# Instrumentação: Router e ProjectRunner emitem eventos
# ---------------------------------------------------------------------------


class TestRouterEmission:
    def test_route_emits_decision(self, obs_db: Path, agents_file: str):
        from aptdata.agents import Router

        Router.from_yaml(agents_file).route("mexer no frontend")
        events = Observer.get().tail(kind="routing.decision")
        assert len(events) == 1
        assert events[0]["payload"]["mode"] == "skill"
        assert events[0]["payload"]["agent_id"] == "zeca"

    def test_route_survives_broken_observer(self, agents_file: str, monkeypatch):
        def _boom(cls):
            raise RuntimeError("observer down")

        monkeypatch.setattr(Observer, "get", classmethod(_boom))
        from aptdata.agents import Router

        d = Router.from_yaml(agents_file).route("mexer no frontend")
        assert d.agent_id == "zeca"  # negócio não pode quebrar


class TestProjectRunnerEmission:
    def test_run_correlates_dispatch_and_response(
        self, obs_db: Path, agents_file: str, monkeypatch
    ):
        from aptdata.agents import Project, ProjectRunner, Router, Task
        from aptdata.agents.base import AgentResponse
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(ok=True, agent_id=self.id, text="done"),
        )
        project = Project(name="p", tasks=[Task(id="a", prompt="backend")])
        ProjectRunner(project, Router.from_yaml(agents_file)).run()

        obs = Observer.get()
        dispatches = obs.tail(kind="agent.dispatch")
        responses = obs.tail(kind="agent.response")
        assert len(dispatches) == 1 and len(responses) == 1
        assert dispatches[0]["run_id"] == responses[0]["run_id"] is not None
        assert responses[0]["payload"]["ok"] is True
        assert responses[0]["payload"]["latency_ms"] >= 0
