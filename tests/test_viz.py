"""Tests for aptdata.viz — servidor de visualização do ecossistema."""

from __future__ import annotations

import json
import textwrap
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from aptdata.viz.server import VizState, _make_handler

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
        keywords: [frontend, tela]
        backend: ondina
        fallback: [zeca]
    """
)


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
    p = tmp_path / "agents.yaml"
    p.write_text(AGENTS_YAML, encoding="utf-8")
    return str(p)


class TestVizState:
    def test_agents_lists_specs(self, agents_file):
        st = VizState(agents_file)
        ags = st.agents()
        assert {a["id"] for a in ags} == {"zeca", "ondina", "holt"}
        # disabled vem por último
        assert ags[-1]["id"] == "holt" and ags[-1]["enabled"] is False
        zeca = next(a for a in ags if a["id"] == "zeca")
        assert zeca["type"] == "openclaw" and "chat" in zeca["capabilities"]

    def test_route_returns_decision(self, agents_file):
        st = VizState(agents_file)
        d = st.route("mexer no frontend")
        assert d.get("agent_id") == "ondina"

    def test_health_maps_all(self, agents_file):
        st = VizState(agents_file)
        h = st.health()
        assert set(h) == {"zeca", "ondina", "holt"}
        assert all(isinstance(v, str) for v in h.values())


def _serve(state: VizState):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(state))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _get_json(base: str, path: str) -> tuple[int, dict]:
    """GET que devolve (status, body-json) mesmo em respostas de erro."""
    try:
        resp = urllib.request.urlopen(base + path, timeout=5)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


class TestVizServer:
    def test_endpoints(self, agents_file):
        st = VizState(agents_file)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(st))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"
        def get(p):
            return json.loads(urllib.request.urlopen(base + p, timeout=5).read())

        try:
            agents = get("/api/agents")
            assert agents["agents"] and len(agents["agents"]) == 3

            rout = get("/api/route?text=mexer%20no%20frontend")
            assert rout.get("agent_id") == "ondina"

            obs = get("/api/observability")
            assert obs["available"] is True

            html = urllib.request.urlopen(base + "/", timeout=5).read().decode()
            assert "aptdata-viz" in html
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_health_endpoint_envelope(self, agents_file):
        httpd, base = _serve(VizState(agents_file))
        try:
            status, data = _get_json(base, "/api/health")
            assert status == 200
            assert set(data["health"]) == {"zeca", "ondina", "holt"}
            assert all(isinstance(v, str) for v in data["health"].values())
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_route_error_returns_503(self, tmp_path):
        # skills inválidas: registry carrega, Router.from_yaml falha -> router None
        broken = AGENTS_YAML + "  - name: quebrada\n"
        p = tmp_path / "agents.yaml"
        p.write_text(broken, encoding="utf-8")
        httpd, base = _serve(VizState(str(p)))
        try:
            status, data = _get_json(base, "/api/route?text=oi")
            assert status == 503
            assert "error" in data
            # o resto da API continua servindo normalmente
            status, data = _get_json(base, "/api/agents")
            assert status == 200 and len(data["agents"]) == 3
        finally:
            httpd.shutdown()
            httpd.server_close()


class TestVizObservability:
    def test_summary_reflects_trace(self, agents_file):
        from aptdata.observability import Observer

        Observer.get().emit("routing.decision", {"mode": "skill"}, agent_id="zeca")
        httpd, base = _serve(VizState(agents_file))
        try:
            status, data = _get_json(base, "/api/observability")
            assert status == 200
            assert data["available"] is True
            assert data["total_events"] >= 1
            assert data["by_kind"]["routing.decision"] >= 1
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_route_via_http_lands_in_trace(self, agents_file):
        """A decisão servida pelo viz é gravada no MESMO store (fonte única)."""
        from aptdata.observability import Observer

        httpd, base = _serve(VizState(agents_file))
        try:
            _get_json(base, "/api/route?text=mexer%20no%20frontend")
            events = Observer.get().tail(kind="routing.decision")
            assert events and events[-1]["payload"]["agent_id"] == "ondina"
        finally:
            httpd.shutdown()
            httpd.server_close()


class TestVizSSE:
    def test_events_stream_sends_backlog(self, agents_file):
        from aptdata.observability import Observer

        Observer.get().emit("agent.response", {"ok": True}, agent_id="zeca")
        httpd, base = _serve(VizState(agents_file))
        try:
            resp = urllib.request.urlopen(base + "/api/events?backlog=5", timeout=5)
            assert resp.headers["Content-Type"].startswith("text/event-stream")
            line = resp.readline()
            while line and not line.startswith(b"data:"):
                line = resp.readline()
            event = json.loads(line[len(b"data:"):].strip())
            assert event["kind"] == "agent.response"
            assert event["agent_id"] == "zeca"
            resp.close()
        finally:
            httpd.shutdown()
            httpd.server_close()


class TestVizStateReload:
    def test_reload_swaps_state_atomically(self, agents_file, monkeypatch):
        """Durante um reload, leitores nunca observam registry/router mistos."""
        import time

        from aptdata.agents import Router

        st = VizState(agents_file)
        assert st.agents()  # carga inicial
        old_registry = st._registry

        in_reload = threading.Event()
        release = threading.Event()
        real_from_yaml = Router.from_yaml.__func__

        def slow_from_yaml(cls, path, **kw):
            in_reload.set()
            assert release.wait(timeout=5)
            return real_from_yaml(cls, path, **kw)

        monkeypatch.setattr(Router, "from_yaml", classmethod(slow_from_yaml))

        # bump de mtime para forçar reload
        p = Path(agents_file)
        p.write_text(AGENTS_YAML, encoding="utf-8")
        now = time.time()
        import os

        os.utime(p, (now + 10, now + 10))

        t = threading.Thread(target=st.agents)
        t.start()
        assert in_reload.wait(timeout=5)
        # o estado antigo tem que continuar publicado até o swap completo
        assert st._registry is old_registry
        release.set()
        t.join(timeout=5)
        assert st._registry is not old_registry
        assert st.route("mexer no frontend").get("agent_id") == "ondina"


def test_cli_registers_viz():
    from typer.testing import CliRunner

    from aptdata.cli.app import app

    r = CliRunner().invoke(app, ["viz", "--help"])
    assert r.exit_code == 0
    assert "aptdata-viz" in r.stdout
