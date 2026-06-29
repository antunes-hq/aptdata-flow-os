"""Tests for aptdata.agents — the uniform agent interface and registry."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.agents import (
    AgentHealth,
    AgentRegistry,
    AgentResponse,
    AgentSpec,
    IAgent,
    OpenClawAgent,
)
from aptdata.agents.registry import _PlaceholderAgent

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_YAML = textwrap.dedent(
    """
    agents:
      ondina:
        name: Ondina
        type: openclaw
        host: localhost
        port: 48330
        endpoint: /api/chat
        capabilities: [frontend, html]
        weight: 8
        enabled: true
      maresia:
        name: Maresia
        type: openclaw
        port: 48331
        capabilities: [backend, frontend]
        weight: 5
        enabled: true
      boleiro:
        name: Boleiro
        type: docker_compose
        capabilities: [copa]
        enabled: true
      lacra:
        name: Lacra
        type: openclaw
        capabilities: [worker]
        enabled: false
    """
)


@pytest.fixture()
def registry(tmp_path: Path) -> AgentRegistry:
    path = tmp_path / "agents.yaml"
    path.write_text(SAMPLE_YAML, encoding="utf-8")
    return AgentRegistry.from_yaml(path)


# ---------------------------------------------------------------------------
# AgentSpec
# ---------------------------------------------------------------------------


class TestAgentSpec:
    def test_base_url_from_host_port(self):
        spec = AgentSpec(
            id="x", name="X", type="openclaw", host="localhost", port=48330
        )
        assert spec.base_url == "http://localhost:48330"

    def test_base_url_none_without_transport(self):
        spec = AgentSpec(id="x", name="X", type="opencode")
        assert spec.base_url is None

    def test_unknown_field_rejected(self):
        with pytest.raises(Exception):
            AgentSpec(id="x", name="X", type="openclaw", bogus=1)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_loads_all_specs(self, registry: AgentRegistry):
        assert len(registry) == 4
        assert "ondina" in registry

    def test_id_injected_from_key(self, registry: AgentRegistry):
        assert registry.spec("maresia").id == "maresia"

    def test_get_returns_iagent(self, registry: AgentRegistry):
        agent = registry.get("ondina")
        assert isinstance(agent, IAgent)
        assert isinstance(agent, OpenClawAgent)

    def test_unknown_type_falls_back_to_placeholder(self, registry: AgentRegistry):
        agent = registry.get("boleiro")
        assert isinstance(agent, _PlaceholderAgent)
        result = agent.send("oi")
        assert result.ok is False
        assert "docker_compose" in (result.error or "")

    def test_get_missing_raises(self, registry: AgentRegistry):
        with pytest.raises(KeyError):
            registry.get("nope")

    def test_specs_can_exclude_disabled(self, registry: AgentRegistry):
        enabled = registry.specs(include_disabled=False)
        assert all(s.enabled for s in enabled)
        assert "lacra" not in {s.id for s in enabled}

    def test_by_capability_sorted_by_weight(self, registry: AgentRegistry):
        agents = registry.by_capability("frontend")
        ids = [a.id for a in agents]
        assert ids == ["ondina", "maresia"]  # weight 8 before 5

    def test_resolve_picks_best(self, registry: AgentRegistry):
        agent = registry.resolve("frontend")
        assert agent is not None and agent.id == "ondina"

    def test_resolve_disabled_excluded(self, registry: AgentRegistry):
        assert registry.resolve("worker") is None  # only lacra, disabled

    def test_resolve_none_for_unknown_capability(self, registry: AgentRegistry):
        assert registry.resolve("inexistente") is None


# ---------------------------------------------------------------------------
# OpenClawAgent
# ---------------------------------------------------------------------------


class TestOpenClawAgent:
    def test_disabled_send_fails_cleanly(self):
        spec = AgentSpec(id="x", name="X", type="openclaw", enabled=False)
        result = OpenClawAgent(spec).send("oi")
        assert result.ok is False and result.error == "agent disabled"

    def test_send_without_transport_fails(self):
        spec = AgentSpec(id="x", name="X", type="openclaw")
        result = OpenClawAgent(spec).send("oi")
        assert result.ok is False and "no host/port" in (result.error or "")

    def test_send_success(self, monkeypatch):
        spec = AgentSpec(
            id="ondina", name="Ondina", type="openclaw", host="localhost", port=48330
        )

        class _Resp:
            status_code = 200

            def json(self):
                return {"reply": "feito"}

        captured = {}

        def _fake_post(url, json, timeout):  # noqa: A002 - mirror requests sig
            captured["url"] = url
            captured["json"] = json
            return _Resp()

        import requests

        monkeypatch.setattr(requests, "post", _fake_post)
        result = OpenClawAgent(spec).send("cria um botao", priority="high")

        assert isinstance(result, AgentResponse)
        assert result.ok is True and result.text == "feito"
        assert captured["url"] == "http://localhost:48330/api/chat"
        assert captured["json"] == {"message": "cria um botao", "priority": "high"}

    def test_send_http_error(self, monkeypatch):
        spec = AgentSpec(
            id="ondina", name="Ondina", type="openclaw", host="localhost", port=48330
        )

        class _Resp:
            status_code = 500
            text = "boom"

        import requests

        monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp())
        result = OpenClawAgent(spec).send("oi")
        assert result.ok is False and "HTTP 500" in (result.error or "")

    def test_health_disabled(self):
        spec = AgentSpec(id="x", name="X", type="openclaw", enabled=False)
        assert OpenClawAgent(spec).health() is AgentHealth.DISABLED
