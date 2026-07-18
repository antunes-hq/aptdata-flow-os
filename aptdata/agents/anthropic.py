"""Anthropic API adapter — chama o SDK Python da Anthropic (Claude).

Diferente do :class:`ClaudeCodeAgent` (que shella pro ``claude -p``), este
adapter fala diretamente com a API REST via ``anthropic`` SDK, sem depender
de CLI local. Suporta:

* Modelos: Opus 4.8 (padrão), Fable 5, Sonnet, Haiku, etc.
* Chave da API via ``ANTHROPIC_API_KEY``.
* ``thinking`` mode (opcional, desligado por padrão para evitar tokens extra).
* ``max_tokens`` configurável por spec.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from aptdata.agents.base import AgentHealth, AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class AnthropicAgent(BaseAgent):
    """Adapter que chama a API do Claude via ``anthropic`` SDK.

    Lê ``ANTHROPIC_API_KEY`` do environment. O modelo vem do ``AgentSpec.model``;
    padrão ``claude-opus-4-8`` se não especificado.
    """

    type = "anthropic"

    #: campos do spec interpretados por este adapter
    _ENV_KEY = "ANTHROPIC_API_KEY"
    _DEFAULT_MODEL = "claude-opus-4-8"

    # ------------------------------------------------------------------
    # send
    # ------------------------------------------------------------------

    def send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        if not self.spec.enabled:
            return AgentResponse(
                ok=False, agent_id=self.id, error="agent disabled"
            )
        try:
            return self._call(prompt, **kwargs)
        except Exception as exc:
            logger.exception("AnthropicAgent[%s] send failed", self.id)
            return AgentResponse(
                ok=False, agent_id=self.id, error=str(exc)
            )

    def _call(self, prompt: str, **kwargs: Any) -> AgentResponse:
        client = self._client()
        model = self.spec.model or self._DEFAULT_MODEL

        # Monta body da requisição
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": self.spec.timeout_ms * 2,  # ~2 tokens/ms
            "messages": [{"role": "user", "content": prompt}],
        }

        # thinking mode (opcional, via spec.note ou kwargs)
        thinking = self._parse_thinking(kwargs.get("thinking"))
        if thinking:
            body["thinking"]={"type": "enabled", "budget_tokens": thinking}
            # Quando thinking tá ligado, não pode mandar temperature
            body.pop("temperature", None)

        # merge extra kwargs que o SDK aceita
        for safe_key in ("temperature", "top_p", "top_k", "stop_sequences",
                         "metadata", "system"):
            if safe_key in kwargs:
                body[safe_key] = kwargs[safe_key]

        logger.debug(
            "AnthropicAgent[%s] calling %s (thinking=%s)",
            self.id, model, bool(thinking),
        )

        resp = client.messages.create(**body)

        # Extrai texto da resposta
        text = self._extract(resp)

        return AgentResponse(
            ok=True,
            agent_id=self.id,
            text=text,
            raw={
                "model": resp.model,
                "stop_reason": resp.stop_reason,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
            },
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _client(self):
        """Retorna cliente Anthropic, validando a chave."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic SDK não instalado. Rode: pip install anthropic"
            ) from None

        api_key = os.environ.get(self._ENV_KEY)
        if not api_key:
            raise ValueError(
                f"{self._ENV_KEY} não definida — não dá pra chamar a API do Claude."
            )
        return Anthropic(api_key=api_key)

    @staticmethod
    def _extract(resp) -> str:
        """Extrai o texto do primeiro content block."""
        if not resp.content:
            return ""
        # content pode ter texto + thinking blocks
        texts = []
        for block in resp.content:
            if hasattr(block, "text") and block.text:
                texts.append(block.text)
        return "\n".join(texts)

    @staticmethod
    def _parse_thinking(raw: Any) -> int | None:
        """Converte spec/param ``thinking`` num budget de tokens, ou None."""
        if raw is None:
            return None
        if isinstance(raw, bool):
            return 16000 if raw else None
        try:
            val = int(raw)
            return max(1024, val)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # health
    # ------------------------------------------------------------------

    def health(self) -> AgentHealth:
        if not self.spec.enabled:
            return AgentHealth.DISABLED
        # Health checa se a env key existe; não bate na API (rate limit caro)
        if os.environ.get(self._ENV_KEY):
            return AgentHealth.UP
        return AgentHealth.DOWN

    def health_deep(self) -> AgentHealth:
        """Health opcional que bate na API de verdade (model: claude-3-haiku)."""
        if not self.spec.enabled:
            return AgentHealth.DISABLED
        try:
            client = self._client()
            client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return AgentHealth.UP
        except Exception:
            return AgentHealth.DOWN
