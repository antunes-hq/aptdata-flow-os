"""CLI-backed agent adapters — Claude Code and OpenCode.

Unlike OpenClaw (which speaks a gateway protocol), these backends are driven
through their command-line interface as stateless one-shot dispatches:

* :class:`ClaudeCodeAgent` — ``claude -p "<prompt>"`` (print mode).
* :class:`OpenCodeAgent` — ``opencode run "<prompt>"``.

Each invocation spawns a fresh session (no shared conversation), which keeps
dispatch stateless and safe. The prompt is always passed as an argv element
(never through a shell) so its content can't inject commands.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

from aptdata.agents.base import AgentHealth, AgentResponse, BaseAgent

logger = logging.getLogger(__name__)


class CLIAgent(BaseAgent):
    """Common machinery for agents driven by a local CLI binary."""

    #: the executable this adapter shells out to; subclasses set it.
    binary: str = ""

    def _build_command(self, prompt: str) -> list[str]:
        """Return the argv list to run for *prompt*. Subclasses implement."""
        raise NotImplementedError

    def send(self, prompt: str, **kwargs: Any) -> AgentResponse:
        if not self.spec.enabled:
            return AgentResponse(ok=False, agent_id=self.id, error="agent disabled")
        if shutil.which(self.binary) is None:
            return AgentResponse(
                ok=False, agent_id=self.id, error=f"'{self.binary}' not found in PATH"
            )

        cmd = self._build_command(prompt)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.spec.timeout_ms / 1000,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return AgentResponse(
                ok=False, agent_id=self.id, error="timeout"
            )
        except OSError as exc:  # pragma: no cover - defensive
            return AgentResponse(ok=False, agent_id=self.id, error=str(exc))

        if proc.returncode != 0:
            return AgentResponse(
                ok=False,
                agent_id=self.id,
                error=(proc.stderr or proc.stdout or "non-zero exit").strip()[:500],
            )
        return AgentResponse(
            ok=True, agent_id=self.id, text=proc.stdout.strip()
        )

    def health(self) -> AgentHealth:
        if not self.spec.enabled:
            return AgentHealth.DISABLED
        return AgentHealth.UP if shutil.which(self.binary) else AgentHealth.DOWN


class ClaudeCodeAgent(CLIAgent):
    """Dispatches to Claude Code via ``claude -p``."""

    type = "claude_code"
    binary = "claude"

    def _build_command(self, prompt: str) -> list[str]:
        cmd = ["claude", "-p", prompt]
        if self.spec.model:
            cmd += ["--model", self.spec.model]
        return cmd


class OpenCodeAgent(CLIAgent):
    """Dispatches to OpenCode via ``opencode run``."""

    type = "opencode"
    binary = "opencode"

    def _build_command(self, prompt: str) -> list[str]:
        cmd = ["opencode", "run", prompt]
        if self.spec.model:
            cmd += ["-m", self.spec.model]
        return cmd
