"""Tests for CLI-backed adapters — ClaudeCodeAgent and OpenCodeAgent."""

from __future__ import annotations

import subprocess

from aptdata.agents import AgentSpec, ClaudeCodeAgent, OpenCodeAgent
from aptdata.agents.base import AgentHealth


def _spec(type_: str, **kw) -> AgentSpec:
    return AgentSpec(id="x", name="X", type=type_, **kw)


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------


class TestCommandBuilding:
    def test_claude_command(self):
        agent = ClaudeCodeAgent(_spec("claude_code", model="claude-opus-4-8"))
        assert agent._build_command("oi") == [
            "claude",
            "-p",
            "oi",
            "--model",
            "claude-opus-4-8",
        ]

    def test_claude_command_no_model(self):
        agent = ClaudeCodeAgent(_spec("claude_code"))
        assert agent._build_command("oi") == ["claude", "-p", "oi"]

    def test_opencode_command(self):
        agent = OpenCodeAgent(_spec("opencode", model="opencode/x"))
        assert agent._build_command("faz") == [
            "opencode",
            "run",
            "faz",
            "-m",
            "opencode/x",
        ]


# ---------------------------------------------------------------------------
# send()
# ---------------------------------------------------------------------------


class TestSend:
    def test_disabled(self):
        agent = ClaudeCodeAgent(_spec("claude_code", enabled=False))
        r = agent.send("oi")
        assert r.ok is False and r.error == "agent disabled"

    def test_binary_missing(self, monkeypatch):
        monkeypatch.setattr("aptdata.agents.cli_agents.shutil.which", lambda b: None)
        r = ClaudeCodeAgent(_spec("claude_code")).send("oi")
        assert r.ok is False and "not found" in (r.error or "")

    def test_success(self, monkeypatch):
        monkeypatch.setattr(
            "aptdata.agents.cli_agents.shutil.which", lambda b: "/usr/bin/" + b
        )
        captured = {}

        def _run(cmd, **kw):
            captured["cmd"] = cmd
            return _Proc(returncode=0, stdout="  pong\n")

        monkeypatch.setattr(subprocess, "run", _run)
        r = OpenCodeAgent(_spec("opencode")).send("ping")
        assert r.ok is True and r.text == "pong"
        assert captured["cmd"] == ["opencode", "run", "ping"]

    def test_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(
            "aptdata.agents.cli_agents.shutil.which", lambda b: "/usr/bin/" + b
        )
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="boom")
        )
        r = ClaudeCodeAgent(_spec("claude_code")).send("oi")
        assert r.ok is False and r.error == "boom"

    def test_timeout(self, monkeypatch):
        monkeypatch.setattr(
            "aptdata.agents.cli_agents.shutil.which", lambda b: "/usr/bin/" + b
        )

        def _run(*a, **k):
            raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

        monkeypatch.setattr(subprocess, "run", _run)
        r = ClaudeCodeAgent(_spec("claude_code")).send("oi")
        assert r.ok is False and r.error == "timeout"


# ---------------------------------------------------------------------------
# health + registry wiring
# ---------------------------------------------------------------------------


class TestHealthAndRegistry:
    def test_health_up_when_binary_present(self, monkeypatch):
        monkeypatch.setattr(
            "aptdata.agents.cli_agents.shutil.which", lambda b: "/usr/bin/" + b
        )
        assert ClaudeCodeAgent(_spec("claude_code")).health() is AgentHealth.UP

    def test_health_down_when_missing(self, monkeypatch):
        monkeypatch.setattr("aptdata.agents.cli_agents.shutil.which", lambda b: None)
        assert OpenCodeAgent(_spec("opencode")).health() is AgentHealth.DOWN

    def test_registry_builds_cli_adapters(self):
        from aptdata.agents.registry import ADAPTERS

        assert ADAPTERS["claude_code"] is ClaudeCodeAgent
        assert ADAPTERS["opencode"] is OpenCodeAgent
