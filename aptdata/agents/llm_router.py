"""LLM Router — usa o Claude (Anthropic API) pra rotear prompts fuzzy.

Injetado como ``LLMRouter`` opcional no :class:`Router`: quando prefix
e skill match não resolvem, pergunta pro Claude qual agente deve cuidar
daquele prompt. O prompt do Claude inclui a lista de agentes disponíveis
e as capacidades deles.
"""

from __future__ import annotations

import logging
import os

from aptdata.agents.base import AgentSpec

logger = logging.getLogger(__name__)

# system prompt pro Claude decidir roteamento
_SYSTEM = """Você é um roteador de mensagens num ecossistema de agentes.
Dado um prompt do usuário e a lista de agentes disponíveis, responda EXATAMENTE
com o id do agente mais adequado (nada mais, nem explicação).

Se o prompt for sobre: code/backend -> maresia, frontend -> ondina,
infra/deploy/docker -> hermez
Revisão/arquitetura/planejamento -> gandalf-api
Monitoramento/infra VPS -> holt
Chat casual -> serginho
Coding/bash/git -> darwin

Se não souber responder, responda apenas: zeca"""


class LLMRouter:
    """Roteador via Claude API, compatível com o tipo ``LLMRouter`` do Router.

    Uso::

        router = Router.from_yaml(
            "agents.yaml", llm=LLMRouter(agents_yaml="agents.yaml")
        )
    """

    _ENV_KEY = "ANTHROPIC_API_KEY"
    _DEFAULT_MODEL = "claude-sonnet-4-20250514"  # rápido e barato pra rotear

    def __init__(
        self,
        agents: list[AgentSpec] | None = None,
        model: str | None = None,
    ) -> None:
        self._agents = agents or []
        self._model = model or self._DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Callable que o Router espera: (text, candidates) -> agent_id | None
    # ------------------------------------------------------------------

    def __call__(self, text: str, candidates: list[AgentSpec]) -> str | None:
        """Pergunta pro Claude qual agente deve cuidar do prompt."""
        if not candidates:
            return None

        # Se a env key não existe, fallback silencioso
        if not os.environ.get(self._ENV_KEY):
            logger.debug("LLMRouter: %s not set, skipping LLM routing", self._ENV_KEY)
            return None

        user_prompt = self._build_prompt(text, candidates)
        try:
            result = self._ask_claude(user_prompt)
        except Exception as exc:
            logger.warning("LLMRouter call failed: %s", exc)
            return None

        # Valida: Claude respondeu com um agente que existe?
        result = result.strip().lower()
        valid_ids = {s.id for s in candidates}
        if result in valid_ids:
            return result

        # Tenta match parcial: Claude pode ter escrito "gandalf-api" como "gandalf_api"
        for vid in valid_ids:
            if vid.replace("-", "_") == result or vid == result.replace("-", "_"):
                return vid

        logger.debug("LLMRouter: Claude devolveu '%s' — não é um agente válido", result)
        return None

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _build_prompt(self, text: str, candidates: list[AgentSpec]) -> str:
        agentes_desc = "\n".join(
            f"- {s.id}: {', '.join(s.capabilities)} ({s.role})"
            for s in sorted(candidates, key=lambda s: s.id)
        )
        return (
            f"Agentes disponíveis:\n{agentes_desc}\n\n"
            f"Prompt do usuário: {text}\n\n"
            f"Qual agente deve lidar com isso? Responda apenas com o id do agente."
        )

    def _ask_claude(self, prompt: str) -> str:
        """Chama o Claude e retorna o texto da resposta."""
        from anthropic import Anthropic  # lazy import

        api_key = os.environ[self._ENV_KEY]
        client = Anthropic(api_key=api_key)

        resp = client.messages.create(
            model=self._model,
            max_tokens=32,  # resposta é tipo "zeca\n" — não precisa de muito
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text if resp.content else ""

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str) -> LLMRouter:
        """Carrega a lista de agentes de um ``agents.yaml``."""
        from pathlib import Path

        import yaml

        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        agents_raw = raw.get("agents", raw)
        specs: list[AgentSpec] = []
        if isinstance(agents_raw, dict):
            for agent_id, body in agents_raw.items():
                body = dict(body or {})
                body.setdefault("id", agent_id)
                specs.append(AgentSpec(**body))
        return cls(agents=specs)
