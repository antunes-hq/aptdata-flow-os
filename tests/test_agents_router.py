"""Tests for aptdata.agents.Router — prefix / skill / llm / default routing."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.agents import AgentRegistry, Router, Skill

ROUTING_YAML = textwrap.dedent(
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
      hermez:
        name: Hermez
        type: openclaw
        capabilities: [deploy]
        weight: 7
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
      - name: devops
        keywords: [deploy, docker]
        backend: hermez
        fallback: [zeca]
      - name: monitoring
        keywords: [status, saude]
        backend: holt
        fallback: [hermez]
    """
)


@pytest.fixture()
def router(tmp_path: Path) -> Router:
    path = tmp_path / "agents.yaml"
    path.write_text(ROUTING_YAML, encoding="utf-8")
    return Router.from_yaml(path)


# ---------------------------------------------------------------------------
# Prefix
# ---------------------------------------------------------------------------


class TestPrefix:
    def test_prefix_wins(self, router: Router):
        d = router.route("/ondina cria um header")
        assert d.mode == "prefix"
        assert d.agent_id == "ondina"
        assert d.text == "cria um header"
        assert d.confidence == 1.0

    def test_prefix_only(self, router: Router):
        d = router.route("/hermez")
        assert d.agent_id == "hermez" and d.text == ""

    def test_unknown_prefix_falls_through(self, router: Router):
        d = router.route("/naoexiste faz algo")
        assert d.mode != "prefix"

    def test_disabled_prefix_falls_through(self, router: Router):
        # holt is disabled -> prefix ignored, no skill match -> default
        d = router.route("/holt status")
        assert d.agent_id != "holt"


# ---------------------------------------------------------------------------
# Skill matching
# ---------------------------------------------------------------------------


class TestSkill:
    def test_keyword_routes(self, router: Router):
        d = router.route("preciso mexer no frontend do app")
        assert d.mode == "skill" and d.agent_id == "ondina"
        assert d.skill == "frontend"

    def test_accent_insensitive(self, router: Router):
        d = router.route("checa a saúde dos containers")  # 'saude' keyword
        assert d.skill == "monitoring"

    def test_disabled_backend_uses_fallback(self, router: Router):
        # monitoring -> holt (disabled) -> fallback hermez
        d = router.route("qual o status agora")
        assert d.mode == "skill" and d.agent_id == "hermez"

    def test_longest_keyword_wins(self, router: Router):
        # both 'deploy' (devops) and nothing else; ensure devops chosen
        d = router.route("faz o deploy no docker")
        assert d.agent_id == "hermez" and d.skill == "devops"


# ---------------------------------------------------------------------------
# Default + LLM
# ---------------------------------------------------------------------------


class TestDefaultAndLLM:
    def test_default_is_entry_point(self, router: Router):
        d = router.route("blablabla sem keyword nenhuma")
        assert d.mode == "default" and d.agent_id == "zeca"

    def test_llm_used_before_default(self, tmp_path: Path):
        path = tmp_path / "agents.yaml"
        path.write_text(ROUTING_YAML, encoding="utf-8")
        registry = AgentRegistry.from_yaml(path)
        skills = [Skill(name="x", keywords=["zzz"], backend="zeca")]
        calls = {}

        def fake_llm(text, candidates):
            calls["text"] = text
            return "hermez"

        r = Router(registry, skills=skills, llm=fake_llm)
        d = r.route("mensagem ambigua")
        assert d.mode == "llm" and d.agent_id == "hermez"
        assert calls["text"] == "mensagem ambigua"

    def test_explicit_default_override(self, tmp_path: Path):
        path = tmp_path / "agents.yaml"
        path.write_text(ROUTING_YAML, encoding="utf-8")
        registry = AgentRegistry.from_yaml(path)
        r = Router(registry, default_agent="ondina")
        assert r.default_agent == "ondina"

    def test_explicit_default_disabled_falls_back(self, tmp_path: Path):
        # holt is disabled -> explicit default must be ignored, heuristic wins
        path = tmp_path / "agents.yaml"
        path.write_text(ROUTING_YAML, encoding="utf-8")
        registry = AgentRegistry.from_yaml(path)
        r = Router(registry, default_agent="holt")
        assert r.default_agent == "zeca"
        d = r.route("blablabla sem keyword nenhuma")
        assert d.mode == "default" and d.agent_id == "zeca"

    def test_llm_choice_disabled_falls_to_default(self, tmp_path: Path):
        # LLM may return any id -> a disabled agent must not be routed to
        path = tmp_path / "agents.yaml"
        path.write_text(ROUTING_YAML, encoding="utf-8")
        registry = AgentRegistry.from_yaml(path)
        r = Router(registry, llm=lambda text, candidates: "holt")
        d = r.route("mensagem ambigua")
        assert d.agent_id != "holt"
        assert d.mode == "default" and d.agent_id == "zeca"
