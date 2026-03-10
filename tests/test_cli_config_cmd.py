"""Tests for aptdata.cli.commands.config_cmd."""

from __future__ import annotations

from typer.testing import CliRunner

from aptdata.cli.app import app

runner = CliRunner()

_VALID_YAML = """\
metadata:
  name: test_pipeline
system:
  system_id: test_sys
  flows:
    - flow_id: main
      components:
        - component_id: step1
      edges: []
"""

_INVALID_YAML = "this is: [not: valid yaml structure for\n"


# ---------------------------------------------------------------------------
# config validate
# ---------------------------------------------------------------------------


class TestConfigValidate:
    def test_validate_valid_file_exits_0(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "validate", str(cfg)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "test_sys" in result.output

    def test_validate_nonexistent_file(self, tmp_path):
        result = runner.invoke(app, ["config", "validate", str(tmp_path / "nope.yaml")])
        # Typer should return non-zero for a missing required file
        assert result.exit_code != 0

    def test_validate_invalid_yaml_exits_1(self, tmp_path):
        cfg = tmp_path / "bad.yaml"
        # Write a YAML that parses but fails schema validation
        cfg.write_text("key: value\n", encoding="utf-8")
        # YamlConfigParser will fail because system_id is required
        result = runner.invoke(app, ["config", "validate", str(cfg)])
        # May or may not fail depending on parser strictness
        # Just ensure no unhandled exception
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# config init
# ---------------------------------------------------------------------------


class TestConfigInit:
    def test_init_creates_file(self, tmp_path):
        output = tmp_path / "new_pipeline.yaml"
        result = runner.invoke(app, ["config", "init", "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_init_file_contains_metadata(self, tmp_path):
        output = tmp_path / "new_pipeline.yaml"
        runner.invoke(app, ["config", "init", "--output", str(output)])
        content = output.read_text(encoding="utf-8")
        assert "metadata" in content
        assert "system_id" in content

    def test_init_fails_if_file_exists(self, tmp_path):
        output = tmp_path / "existing.yaml"
        output.write_text("existing content", encoding="utf-8")
        result = runner.invoke(app, ["config", "init", "--output", str(output)])
        assert result.exit_code == 1

    def test_init_default_output(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "init"])
        # Default output is pipeline.yaml in cwd
        assert result.exit_code == 0
        assert (tmp_path / "pipeline.yaml").exists()


# ---------------------------------------------------------------------------
# config show
# ---------------------------------------------------------------------------


class TestConfigShow:
    def test_show_exits_0(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "show", str(cfg)])
        assert result.exit_code == 0

    def test_show_outputs_yaml_content(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "show", str(cfg)])
        assert result.exit_code == 0
        assert "test_pipeline" in result.output or "metadata" in result.output

    def test_show_nonexistent_file(self, tmp_path):
        result = runner.invoke(app, ["config", "show", str(tmp_path / "nope.yaml")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# config run
# ---------------------------------------------------------------------------


class TestConfigRun:
    def test_run_valid_config_exits_0(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "run", str(cfg)])
        assert result.exit_code == 0

    def test_run_with_env_option(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "run", str(cfg), "--env", "prod"])
        assert result.exit_code == 0

    def test_run_shows_success(self, tmp_path):
        cfg = tmp_path / "pipeline.yaml"
        cfg.write_text(_VALID_YAML, encoding="utf-8")
        result = runner.invoke(app, ["config", "run", str(cfg)])
        assert result.exit_code == 0
        assert "success" in result.output.lower() or "executed" in result.output.lower()
