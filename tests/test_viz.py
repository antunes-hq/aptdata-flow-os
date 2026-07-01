"""Tests for aptdata.viz — servidor de visualização do ecossistema."""

from __future__ import annotations

import json
import textwrap
import threading
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
            assert obs["available"] is False

            html = urllib.request.urlopen(base + "/", timeout=5).read().decode()
            assert "aptdata-viz" in html
        finally:
            httpd.shutdown()
            httpd.server_close()


def test_cli_registers_viz():
    from typer.testing import CliRunner

    from aptdata.cli.app import app

    r = CliRunner().invoke(app, ["viz", "--help"])
    assert r.exit_code == 0
    assert "aptdata-viz" in r.stdout
