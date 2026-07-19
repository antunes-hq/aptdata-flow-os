"""Tests for ``aptdata init`` and ``aptdata doctor`` (ADR-002 §2.2/§2.4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aptdata.cli.app import app
from aptdata.cli.commands.doctor_cmd import run_doctor
from aptdata.cli.commands.init_cmd import (
    _STARTER_AGENTS_YAML,
    _STARTER_CONFIG_YAML,
    _STARTER_SYSTEM_YAML,
    _migrate_legacy_files,
    _write_schemas,
    _write_starter_files,
)
from aptdata.config.loader import (
    APTDATA_DIR_NAME,
    ProjectConfig,
    locate_project,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project(root: Path) -> ProjectConfig:
    return ProjectConfig(root=root, aptdata_dir=root / APTDATA_DIR_NAME)


# ---------------------------------------------------------------------------
# aptdata init (no --migrate)
# ---------------------------------------------------------------------------


class TestInitCreate:
    def test_init_creates_dotdir_and_three_yamls(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0, result.output

        aptdata = tmp_path / APTDATA_DIR_NAME
        assert aptdata.is_dir()
        assert (aptdata / "system.yaml").is_file()
        assert (aptdata / "agents.yaml").is_file()
        assert (aptdata / "config.yaml").is_file()

    def test_init_writes_versioned_json_schemas(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0

        schemas = tmp_path / APTDATA_DIR_NAME / "schemas"
        assert (schemas / "config.json").is_file()
        assert (schemas / "agents.json").is_file()
        assert (schemas / "system.json").is_file()
        for name in ("config", "agents", "system"):
            loaded = json.loads((schemas / f"{name}.json").read_text(encoding="utf-8"))
            assert loaded["type"] == "object"

    def test_init_starter_agents_yaml_is_valid_against_schema(self, tmp_path: Path):
        """The starter file we write must validate against the schema we write."""
        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0

        # doctor should pass on the freshly-init'd project
        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_init_is_idempotent_without_force(self, tmp_path: Path):
        """Re-running init keeps existing files (does NOT overwrite)."""
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        # Mutate agents.yaml so we can detect whether init clobbered it.
        agents = tmp_path / APTDATA_DIR_NAME / "agents.yaml"
        agents.write_text("# user-edited\nagents: {}\n", encoding="utf-8")

        result = runner.invoke(app, ["init", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "user-edited" in agents.read_text(encoding="utf-8")

    def test_init_force_overwrites_starter_files(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        agents = tmp_path / APTDATA_DIR_NAME / "agents.yaml"
        agents.write_text("# user-edited\n", encoding="utf-8")

        result = runner.invoke(app, ["init", "--path", str(tmp_path), "--force"])
        assert result.exit_code == 0
        assert "user-edited" not in agents.read_text(encoding="utf-8")

    def test_init_json_mode_emits_one_line_per_action(self, tmp_path: Path):
        result = runner.invoke(app, ["init", "--path", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        payloads = [json.loads(line) for line in lines]
        # 3 writes (yamls) + 3 schemas + 1 done = at least 7
        assert len(payloads) >= 7
        assert any(p.get("action") == "done" for p in payloads)
        assert any(p.get("action") == "write" for p in payloads)
        assert any(p.get("action") == "schema" for p in payloads)

    def test_init_refuses_to_nest_inside_existing_project(self, tmp_path: Path):
        # Create a project at tmp_path first.
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        # Now try to init a subdirectory of it.
        nested = tmp_path / "subdir"
        nested.mkdir()

        result = runner.invoke(app, ["init", "--path", str(nested)])
        assert result.exit_code == 1, result.output
        assert (
            "refusing to nest" in result.output.lower()
            or "nest" in result.output.lower()
        )


# ---------------------------------------------------------------------------
# aptdata init --migrate
# ---------------------------------------------------------------------------


class TestInitMigrate:
    def test_migrate_moves_legacy_files_into_dotdir(self, tmp_path: Path):
        # Legacy root-level files
        (tmp_path / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
        (tmp_path / "aptdata.yaml").write_text(
            "system: {id: legacy}\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["init", "--migrate", "--path", str(tmp_path)])
        assert result.exit_code == 0, result.output

        # Legacy files are GONE (move, not copy)
        assert not (tmp_path / "agents.yaml").exists()
        assert not (tmp_path / "aptdata.yaml").exists()

        # And appear inside .aptdata/ (aptdata.yaml renamed to system.yaml)
        aptdata = tmp_path / APTDATA_DIR_NAME
        assert (aptdata / "agents.yaml").is_file()
        assert (aptdata / "system.yaml").is_file()
        assert "legacy" in (aptdata / "system.yaml").read_text(encoding="utf-8")

    def test_migrate_writes_starter_config_yaml_when_absent(self, tmp_path: Path):
        # Only legacy agents.yaml exists; config.yaml has no legacy counterpart.
        (tmp_path / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")

        result = runner.invoke(app, ["init", "--migrate", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / APTDATA_DIR_NAME / "config.yaml").is_file()

    def test_migrate_does_not_overwrite_existing_dotdir_files_without_force(
        self, tmp_path: Path
    ):
        # Pre-existing .aptdata/agents.yaml + legacy root agents.yaml
        aptdata = tmp_path / APTDATA_DIR_NAME
        aptdata.mkdir()
        (aptdata / "agents.yaml").write_text("# existing\n", encoding="utf-8")
        (tmp_path / "agents.yaml").write_text("# legacy\n", encoding="utf-8")

        result = runner.invoke(app, ["init", "--migrate", "--path", str(tmp_path)])
        assert result.exit_code == 0
        # The existing file is preserved
        assert "existing" in (aptdata / "agents.yaml").read_text(encoding="utf-8")
        # And the legacy file is NOT moved (skipped because target exists)
        assert (tmp_path / "agents.yaml").exists()

    def test_migrate_force_overwrites_existing_dotdir_files(self, tmp_path: Path):
        aptdata = tmp_path / APTDATA_DIR_NAME
        aptdata.mkdir()
        (aptdata / "agents.yaml").write_text("# existing\n", encoding="utf-8")
        (tmp_path / "agents.yaml").write_text("# legacy\n", encoding="utf-8")

        result = runner.invoke(
            app, ["init", "--migrate", "--force", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "legacy" in (aptdata / "agents.yaml").read_text(encoding="utf-8")
        assert not (tmp_path / "agents.yaml").exists()

    def test_migrate_emits_action_records_in_json(self, tmp_path: Path):
        (tmp_path / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")

        result = runner.invoke(
            app, ["init", "--migrate", "--path", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        payloads = [
            json.loads(line)
            for line in result.output.strip().splitlines()
            if line.strip()
        ]
        migrate_actions = [p for p in payloads if p.get("action") == "migrate"]
        assert len(migrate_actions) == 1
        assert "agents.yaml" in migrate_actions[0]["from"]


# ---------------------------------------------------------------------------
# _migrate_legacy_files / _write_starter_files / _write_schemas (unit)
# ---------------------------------------------------------------------------


class TestMigrationHelpers:
    def test_migrate_legacy_files_returns_action_records(self, tmp_path: Path):
        (tmp_path / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
        project = _project(tmp_path)
        project.aptdata_dir.mkdir()

        actions = _migrate_legacy_files(tmp_path, project, force=False)
        assert len(actions) == 1
        assert actions[0]["action"] == "migrate"
        assert "agents.yaml" in actions[0]["from"]

    def test_migrate_legacy_files_empty_when_no_legacies(self, tmp_path: Path):
        project = _project(tmp_path)
        project.aptdata_dir.mkdir()
        assert _migrate_legacy_files(tmp_path, project, force=False) == []

    def test_write_starter_files_writes_three_yamls(self, tmp_path: Path):
        project = _project(tmp_path)
        project.aptdata_dir.mkdir()

        actions = _write_starter_files(project, force=False)
        assert (project.aptdata_dir / "system.yaml").is_file()
        assert (project.aptdata_dir / "agents.yaml").is_file()
        assert (project.aptdata_dir / "config.yaml").is_file()
        assert len(actions) == 3

    def test_write_starter_files_keeps_existing_without_force(self, tmp_path: Path):
        project = _project(tmp_path)
        project.aptdata_dir.mkdir()
        (project.aptdata_dir / "agents.yaml").write_text(
            "# existing\n", encoding="utf-8"
        )

        actions = _write_starter_files(project, force=False)
        keep = [a for a in actions if a["action"] == "keep"]
        assert len(keep) == 1
        assert "existing" in (project.aptdata_dir / "agents.yaml").read_text(
            encoding="utf-8"
        )

    def test_write_schemas_writes_three_json_files(self, tmp_path: Path):
        project = _project(tmp_path)
        project.aptdata_dir.mkdir()

        actions = _write_schemas(project)
        assert len(actions) == 3
        assert (project.aptdata_dir / "schemas" / "agents.json").is_file()
        assert (project.aptdata_dir / "schemas" / "config.json").is_file()
        assert (project.aptdata_dir / "schemas" / "system.json").is_file()

    def test_starter_templates_are_not_empty(self):
        assert _STARTER_SYSTEM_YAML.strip()
        assert _STARTER_AGENTS_YAML.strip()
        assert _STARTER_CONFIG_YAML.strip()
        assert "agents:" in _STARTER_AGENTS_YAML
        assert "system:" in _STARTER_SYSTEM_YAML


# ---------------------------------------------------------------------------
# aptdata doctor
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_passes_on_fresh_init(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "doctor ok" in result.output

    def test_doctor_fails_when_agents_yaml_missing(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        (tmp_path / APTDATA_DIR_NAME / "agents.yaml").unlink()

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "agents.yaml" in result.output
        assert "missing" in result.output.lower() or "required" in result.output.lower()

    def test_doctor_fails_when_agents_yaml_invalid(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        (tmp_path / APTDATA_DIR_NAME / "agents.yaml").write_text(
            "agents: not-a-mapping\n", encoding="utf-8"
        )

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "agents.yaml" in result.output

    def test_doctor_warns_on_optional_config_missing(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        (tmp_path / APTDATA_DIR_NAME / "config.yaml").unlink()

        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        # config.yaml is optional — doctor still passes overall.
        assert result.exit_code == 0
        assert "config.yaml" in result.output
        assert "optional" in result.output.lower()

    def test_doctor_json_mode_emits_report(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        result = runner.invoke(app, ["doctor", "--path", str(tmp_path), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output.strip())
        assert payload["ok"] is True
        assert payload["project_root"] == str(tmp_path.resolve())
        assert len(payload["checks"]) == 3
        assert {c["file"] for c in payload["checks"]} == {
            "system.yaml",
            "agents.yaml",
            "config.yaml",
        }

    def test_doctor_exits_1_when_no_dotdir(self, tmp_path: Path):
        # tmp_path has no .aptdata/ up the tree.
        result = runner.invoke(app, ["doctor", "--path", str(tmp_path)])
        assert result.exit_code == 1
        assert "init" in result.output  # hint to run init

    def test_run_doctor_returns_dict_with_ok_and_checks(self, tmp_path: Path):
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        project = locate_project(tmp_path)

        report = run_doctor(project)
        assert "ok" in report
        assert "checks" in report
        assert len(report["checks"]) == 3
        for check in report["checks"]:
            assert {"file", "ok", "required", "detail"} <= set(check)


# ---------------------------------------------------------------------------
# Consumers integration: agents_cmd reads from .aptdata/
# ---------------------------------------------------------------------------


class TestConsumersReadDotdir:
    def test_agents_list_reads_from_dotdir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Read from .aptdata/ when --file is omitted."""
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        agents_yaml = tmp_path / APTDATA_DIR_NAME / "agents.yaml"
        agents_yaml.write_text(
            "agents:\n"
            "  testbot:\n"
            "    name: TestBot\n"
            "    type: openclaw\n"
            "    host: localhost\n"
            "    port: 48330\n"
            "    capabilities: [chat]\n"
            "    enabled: true\n",
            encoding="utf-8",
        )

        # Run from inside the project so CWD-based discovery finds .aptdata/.
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["agents", "list", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["count"] == 1
        assert payload["agents"][0]["id"] == "testbot"

    def test_default_mode_in_dotdir_is_respected_by_cli(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """PR3 (ADR-002 §2.3) — ``default_mode`` no ``.aptdata/agents.yaml``
        vira o default do ``--mode`` em todos os comandos de execução do CLI."""
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        agents_yaml = tmp_path / APTDATA_DIR_NAME / "agents.yaml"
        agents_yaml.write_text(
            "default_mode: orchestrated\n"
            "agents:\n"
            "  testbot:\n"
            "    name: TestBot\n"
            "    type: openclaw\n"
            "    host: localhost\n"
            "    port: 48330\n"
            "    capabilities: [chat]\n"
            "    enabled: true\n",
            encoding="utf-8",
        )

        # stub do send para o dry-run não precisar de rede
        from aptdata.agents.base import AgentResponse
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(
                ok=True, agent_id=self.id, text=f"re:{p}"
            ),
        )

        monkeypatch.chdir(tmp_path)
        # send sem --mode → cai no default_mode do projeto (orchestrated).
        # (send ainda usa o agent_id explícito, mas o campo `mode` no JSON
        # reflete o modo efetivo, que aqui é o default do projeto.)
        result = runner.invoke(app, ["agents", "send", "testbot", "oi", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output.strip())
        assert payload["mode"] == "orchestrated"
        assert payload["ok"] is True

    def test_explicit_mode_overrides_project_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """``--mode`` explícito vence o ``default_mode`` do projeto."""
        runner.invoke(app, ["init", "--path", str(tmp_path)])
        agents_yaml = tmp_path / APTDATA_DIR_NAME / "agents.yaml"
        agents_yaml.write_text(
            "default_mode: orchestrated\n"
            "agents:\n"
            "  testbot:\n"
            "    name: TestBot\n"
            "    type: openclaw\n"
            "    host: localhost\n"
            "    port: 48330\n"
            "    capabilities: [chat]\n"
            "    enabled: true\n",
            encoding="utf-8",
        )

        from aptdata.agents.base import AgentResponse
        from aptdata.agents.openclaw import OpenClawAgent

        monkeypatch.setattr(
            OpenClawAgent,
            "send",
            lambda self, p, **k: AgentResponse(
                ok=True, agent_id=self.id, text=f"re:{p}"
            ),
        )
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "agents",
                "send",
                "testbot",
                "oi",
                "--json",
                "--mode",
                "oneshot",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output.strip())["mode"] == "oneshot"
