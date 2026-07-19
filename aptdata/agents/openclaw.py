"""OpenClaw backend adapter.

OpenClaw workers (Zeca, Ondina, Maresia, Hermez, ...) expose an HTTP chat
endpoint (default ``/api/chat`` on ports 48330-48333). This adapter isolates
that transport so the rest of aptdata only ever sees :class:`IAgent`.
"""

from __future__ import annotations

import logging
from typing import Any

from aptdata.agents.base import AgentHealth, AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class OpenClawAgent(BaseAgent):
    """Talks to an OpenClaw worker over HTTP."""

    type = "openclaw"

    def _endpoint(self) -> str | None:
        base = self.spec.base_url
        if not base:
            return None
        path = self.spec.endpoint or "/api/chat"
        return f"{base}{path}"

    def _do_send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        url = self._endpoint()
        if not url:
            return AgentResponse(
                ok=False,
                agent_id=self.id,
                error="no host/port configured for OpenClaw agent",
            )

        import requests  # lazy: keeps core import-light, mirrors integrations/

        payload = {"message": prompt, **kwargs}
        try:
            resp = requests.post(url, json=payload, timeout=self.spec.timeout_ms / 1000)
        except requests.RequestException as exc:
            logger.warning("OpenClaw %s unreachable: %s", self.id, exc)
            return AgentResponse(ok=False, agent_id=self.id, error=str(exc))

        if resp.status_code != 200:
            return AgentResponse(
                ok=False,
                agent_id=self.id,
                error=f"HTTP {resp.status_code}",
                raw={"status": resp.status_code, "body": resp.text[:500]},
            )

        data = self._parse(resp)
        text = self._extract_text(data)
        return AgentResponse(ok=True, agent_id=self.id, text=text, raw=data)

    @staticmethod
    def _parse(resp: Any) -> dict[str, Any]:
        try:
            data = resp.json()
            return data if isinstance(data, dict) else {"value": data}
        except ValueError:
            return {"text": resp.text}

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        for key in ("reply", "response", "message", "text", "output"):
            value = data.get(key)
            if isinstance(value, str):
                return value
        return ""

    def health(self) -> AgentHealth:
        if not self.spec.enabled:
            return AgentHealth.DISABLED
        url = self.spec.base_url
        if not url:
            return AgentHealth.UNKNOWN
        import requests

        try:
            resp = requests.get(url, timeout=3)
            return AgentHealth.UP if resp.status_code < 500 else AgentHealth.DOWN
        except requests.RequestException:
            return AgentHealth.DOWN
