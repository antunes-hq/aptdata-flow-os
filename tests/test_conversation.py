"""Tests for aptdata.agents.conversation — ConversationEngine (headless).

Contrato (docs/plans/telegram-orchestration.md §3, Fases 0-1):
- prefix / skill com confiança alta  → DISPATCH direto
- skill médio (0.5 ≤ conf < 0.75) e llm → NEEDS_CONFIRMATION
- default / none                     → NEEDS_CLARIFICATION
- capability destrutiva (guardrail)  → SEMPRE confirmação, ignora confiança
- follow-up multi-turno reusa session.last_agent sem re-rotear
- thresholds/guardrails vêm do bloco ``routing:`` do agents.yaml
- cada turno emite eventos de observabilidade (permission.requested/resolved)
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from aptdata.agents import Router
from aptdata.agents.base import AgentResponse
from aptdata.agents.conversation import ConversationEngine, DecisionPolicy
from aptdata.observability import Observer

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
      hermez:
        name: Hermez
        type: openclaw
        capabilities: [deploy]
        weight: 7
        enabled: true
    skills:
      - name: frontend
        keywords: [frontend, tela]
        backend: ondina
        fallback: [zeca]
      - name: devops
        keywords: [deploy]
        backend: hermez
    routing:
      dispatch_above: 0.75
      guarded_capabilities: [deploy, ssh, docker]
    """
)


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
    p = tmp_path / "agents.yaml"
    p.write_text(AGENTS_YAML, encoding="utf-8")
    return str(p)


@pytest.fixture()
def engine(agents_file: str, tmp_path: Path, monkeypatch) -> ConversationEngine:
    monkeypatch.setenv("APTDATA_SESSIONS_DIR", str(tmp_path / "sessions"))
    from aptdata.agents.openclaw import OpenClawAgent

    monkeypatch.setattr(
        OpenClawAgent,
        "send",
        lambda self, p, **k: AgentResponse(ok=True, agent_id=self.id, text=f"re:{p}"),
    )
    return ConversationEngine.from_yaml(agents_file)


class TestPolicy:
    def test_prefix_dispatches_directly(self, engine: ConversationEngine):
        turn = engine.handle("s1", "/ondina cria um header")
        assert turn.type == "dispatched"
        assert turn.decision.agent_id == "ondina"
        assert turn.response.ok is True

    def test_high_confidence_skill_dispatches(self, engine: ConversationEngine):
        # keyword longa vs texto curto -> confidence >= 0.75
        turn = engine.handle("s1", "mexer no frontend")
        assert turn.type == "dispatched"
        assert turn.decision.agent_id == "ondina"

    def test_mid_confidence_skill_asks_confirmation(self, engine: ConversationEngine):
        # keyword curta em texto longo -> 0.5 <= conf < 0.75
        turn = engine.handle(
            "s1", "quero dar um jeito naquela tela quebrada do sistema de vendas"
        )
        assert turn.type == "needs_confirmation"
        assert turn.decision.agent_id == "ondina"
        assert turn.decision_id
        assert "ondina" in turn.candidates and "zeca" in turn.candidates

    def test_default_mode_asks_clarification(self, engine: ConversationEngine):
        turn = engine.handle("s1", "blablabla sem sinal nenhum")
        assert turn.type == "needs_clarification"
        assert turn.decision.mode == "default"

    def test_guarded_capability_always_confirms(self, engine: ConversationEngine):
        # prefix teria confiança 1.0, mas hermez tem capability 'deploy' (guarded)
        turn = engine.handle("s1", "/hermez sobe a nova versao")
        assert turn.type == "needs_confirmation"
        assert turn.decision.agent_id == "hermez"


class TestConfirmFlow:
    def test_confirm_dispatches_pending(self, engine: ConversationEngine):
        ask = engine.handle("s1", "/hermez deploy do painel")
        assert ask.type == "needs_confirmation"
        done = engine.confirm("s1", ask.decision_id)
        assert done.type == "dispatched"
        assert done.decision.agent_id == "hermez"
        assert done.response.text.startswith("re:")

    def test_confirm_with_choice_overrides_agent(self, engine: ConversationEngine):
        ask = engine.handle("s1", "/hermez deploy do painel")
        done = engine.confirm("s1", ask.decision_id, choice="zeca")
        assert done.type == "dispatched"
        assert done.decision.agent_id == "zeca"
        assert done.decision.mode == "override"

    def test_unknown_decision_id_is_reply(self, engine: ConversationEngine):
        turn = engine.confirm("s1", "nao-existe")
        assert turn.type == "reply"

    def test_confirm_emits_permission_events(self, engine: ConversationEngine):
        ask = engine.handle("s1", "/hermez deploy")
        engine.confirm("s1", ask.decision_id)
        obs = Observer.get()
        assert obs.tail(kind="permission.requested")
        resolved = obs.tail(kind="permission.resolved")
        assert resolved and resolved[-1]["payload"]["approved"] is True


class TestMultiTurn:
    def test_followup_reuses_last_agent(self, engine: ConversationEngine):
        first = engine.handle("s1", "mexer no frontend")
        assert first.decision.agent_id == "ondina"
        follow = engine.handle("s1", "continua")
        assert follow.type == "dispatched"
        assert follow.decision.agent_id == "ondina"
        assert follow.decision.mode == "followup"

    def test_followup_without_history_clarifies(self, engine: ConversationEngine):
        turn = engine.handle("fresh-session", "continua")
        assert turn.type == "needs_clarification"

    def test_sessions_are_isolated(self, engine: ConversationEngine):
        engine.handle("s1", "mexer no frontend")
        turn = engine.handle("s2", "continua")
        assert turn.type == "needs_clarification"

    def test_session_persists_across_instances(
        self, engine: ConversationEngine, agents_file: str
    ):
        engine.handle("s1", "mexer no frontend")
        rebuilt = ConversationEngine.from_yaml(agents_file)
        follow = rebuilt.handle("s1", "continua")
        assert follow.type == "dispatched"
        assert follow.decision.agent_id == "ondina"


class TestPolicyConfig:
    def test_thresholds_come_from_yaml(self, tmp_path: Path):
        yaml_text = AGENTS_YAML.replace("dispatch_above: 0.75", "dispatch_above: 0.99")
        p = tmp_path / "agents.yaml"
        p.write_text(yaml_text, encoding="utf-8")
        policy = DecisionPolicy.from_yaml(p)
        assert policy.dispatch_above == 0.99
        assert "deploy" in policy.guarded_capabilities

    def test_defaults_without_routing_block(self, tmp_path: Path):
        p = tmp_path / "agents.yaml"
        p.write_text("agents:\n  a:\n    name: A\n    type: openclaw\n", "utf-8")
        policy = DecisionPolicy.from_yaml(p)
        assert policy.dispatch_above == 0.75
        assert policy.guarded_capabilities  # defaults seguros

    def test_turn_to_dict_is_json_ready(self, engine: ConversationEngine):
        import json

        turn = engine.handle("s1", "/ondina oi")
        assert json.dumps(turn.to_dict())
        assert turn.to_dict()["type"] == "dispatched"


class TestRouterStillWorks:
    def test_engine_uses_same_router_contract(self, agents_file: str):
        router = Router.from_yaml(agents_file)
        assert router.route("/ondina oi").agent_id == "ondina"
