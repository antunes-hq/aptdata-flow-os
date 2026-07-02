"""CLI tests for ``aptdata setup`` — diagnóstico e configuração guiada."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aptdata.cli.app import app

runner = CliRunner()

AGENTS_YAML = textwrap.dedent(
    """
    agents:
      zeca:
        name: Zeca
        type: openclaw
        role: porta_de_entrada
        capabilities: [chat]
        weight: 10
        enabled: true
    skills:
      - name: frontend
        keywords: [frontend]
        backend: zeca
    routing:
      guarded_capabilities: [deploy]
    """
)


@pytest.fixture()
def agents_file(tmp_path: Path) -> str:
    p = tmp_path / "agents.yaml"
    p.write_text(AGENTS_YAML, encoding="utf-8")
    return str(p)


class TestSetupCheck:
    def test_ok_when_agents_file_valid(self, agents_file, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        r = runner.invoke(app, ["setup", "--check", "-f", agents_file, "--json"])
        assert r.exit_code == 0
        data = json.loads(r.stdout)
        assert data["ok"] is True
        by_id = {c["id"]: c for c in data["checks"]}
        assert by_id["agents_file"]["ok"] is True
        assert by_id["router"]["ok"] is True
        assert by_id["routing_policy"]["ok"] is True
        # telegram é opcional: sem token -> check aparece como não-ok mas não derruba
        assert by_id["telegram_token"]["ok"] is False
        assert by_id["telegram_token"]["required"] is False

    def test_fails_without_agents_file(self, tmp_path, monkeypatch):
        r = runner.invoke(
            app,
            ["setup", "--check", "-f", str(tmp_path / "nope.yaml"), "--json"],
        )
        assert r.exit_code == 1
        data = json.loads(r.stdout)
        assert data["ok"] is False
        by_id = {c["id"]: c for c in data["checks"]}
        assert by_id["agents_file"]["ok"] is False

    def test_telegram_ok_when_token_and_transport(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        p = tmp_path / "agents.yaml"
        p.write_text(
            AGENTS_YAML
            + "transports:\n  telegram:\n    chat_id: '42'\n"
            + "    token_env: TELEGRAM_BOT_TOKEN\n",
            encoding="utf-8",
        )
        r = runner.invoke(app, ["setup", "--check", "-f", str(p), "--json"])
        assert r.exit_code == 0
        by_id = {c["id"]: c for c in json.loads(r.stdout)["checks"]}
        assert by_id["telegram_token"]["ok"] is True
        assert by_id["telegram_transport"]["ok"] is True

    def test_text_mode_renders_all_checks(self, agents_file):
        r = runner.invoke(app, ["setup", "--check", "-f", agents_file])
        assert r.exit_code == 0
        assert "agents_file" in r.stdout and "telegram" in r.stdout


class TestSetupWizard:
    def test_creates_starter_agents_yaml(self, tmp_path, monkeypatch):
        from aptdata.cli.commands import setup_cmd

        target = tmp_path / "agents.yaml"
        monkeypatch.setattr(setup_cmd, "_confirm", lambda msg, default=True: True)
        monkeypatch.setattr(setup_cmd, "_text", lambda msg, default="": "")
        r = runner.invoke(app, ["setup", "-f", str(target)])
        assert r.exit_code == 0
        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "agents:" in content and "routing:" in content

    def test_configures_telegram_transport(self, agents_file, monkeypatch):
        from aptdata.cli.commands import setup_cmd

        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        monkeypatch.setattr(setup_cmd, "_confirm", lambda msg, default=True: True)
        monkeypatch.setattr(setup_cmd, "_text", lambda msg, default="": "4242")
        monkeypatch.setattr(
            setup_cmd, "_telegram_get_me",
            lambda token: {"ok": True, "result": {"username": "meu_bot"}},
        )
        r = runner.invoke(app, ["setup", "-f", agents_file])
        assert r.exit_code == 0
        content = Path(agents_file).read_text(encoding="utf-8")
        assert "transports:" in content
        assert "chat_id: '4242'" in content or 'chat_id: "4242"' in content
        # segredo NUNCA vai para o arquivo — só o nome da env var
        assert "123:abc" not in content
        assert "TELEGRAM_BOT_TOKEN" in content
