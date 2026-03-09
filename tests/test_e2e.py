"""End-to-end tests — exercise the CLI as a user would from the command line.

Tests are marked ``@pytest.mark.e2e``.  They test complete workflows through
the Typer CLI using ``CliRunner`` and verify JSON-line output semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.conftest import assert_json_event, parse_json_lines


# ---------------------------------------------------------------------------
# Scaffold E2E
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestScaffoldE2E:
    """End-to-end scaffold command scenarios."""

    def test_scaffold_hello_world_complete_flow(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Scaffold hello-world; verify started + completed events and files."""
        result = cli_runner.invoke(
            cli_app,
            ["scaffold", "e2e_project", "--output", str(tmp_path)],
        )
        assert result.exit_code == 0
        started = assert_json_event(result.output, "scaffold.started")
        assert started["project"] == "e2e_project"
        assert started["template"] == "hello-world"

        completed = assert_json_event(result.output, "scaffold.completed")
        assert completed["project"] == "e2e_project"

        project_dir = Path(completed["path"])
        assert (project_dir / "main.py").exists()
        assert (project_dir / "README.md").exists()

    def test_scaffold_fails_on_invalid_name(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Project names with invalid chars produce a scaffold.error event."""
        result = cli_runner.invoke(
            cli_app,
            ["scaffold", "123-invalid", "--output", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_scaffold_fails_on_duplicate_directory(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Re-scaffolding into an existing directory must fail."""
        cli_runner.invoke(cli_app, ["scaffold", "dup_proj", "--output", str(tmp_path)])
        result = cli_runner.invoke(
            cli_app, ["scaffold", "dup_proj", "--output", str(tmp_path)]
        )
        assert result.exit_code != 0

    def test_scaffold_all_templates_succeed(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Every template should scaffold without errors."""
        from smart_data.cli.scaffold import TEMPLATE_NAMES

        for i, template in enumerate(TEMPLATE_NAMES):
            project = f"proj_{i}"
            result = cli_runner.invoke(
                cli_app,
                ["scaffold", project, "--output", str(tmp_path), "--template", template],
            )
            assert result.exit_code == 0, f"Template {template!r} failed: {result.output}"

    def test_scaffold_unknown_template_exits_nonzero(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """An unknown template must exit with non-zero code."""
        result = cli_runner.invoke(
            cli_app,
            ["scaffold", "some_proj", "--output", str(tmp_path), "--template", "does-not-exist"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Mesh CLI E2E
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestMeshE2E:
    """End-to-end mesh CLI scenarios."""

    def test_mesh_list_empty_directory(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh list on an empty dir returns count=0 in JSON mode."""
        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["count"] == 0
        assert data["components"] == []

    def test_mesh_list_after_scaffold_job_wheel(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh list finds job-wheel component after scaffolding."""
        cli_runner.invoke(
            cli_app,
            ["scaffold", "e2e_job", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["count"] == 1
        comp = data["components"][0]
        assert comp["component"] == "e2e_job"
        assert comp["type"] == "job-wheel"

    def test_mesh_list_after_scaffold_docker_compose(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh list finds docker-compose-app component after scaffolding."""
        cli_runner.invoke(
            cli_app,
            ["scaffold", "e2e_app", "--output", str(tmp_path), "--template", "docker-compose-app"],
        )
        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["count"] == 1
        comp = data["components"][0]
        assert comp["type"] == "docker-compose-app"

    def test_mesh_run_dry_run_job_wheel_events(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh run --dry-run emits started and dry_run events in order."""
        cli_runner.invoke(
            cli_app,
            ["scaffold", "e2e_runjob", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        result = cli_runner.invoke(
            cli_app,
            ["mesh", "run", "e2e_runjob", "--dir", str(tmp_path), "--dry-run", "--json"],
        )
        assert result.exit_code == 0
        events = parse_json_lines(result.output)
        event_names = [e.get("event") for e in events]
        assert "mesh.run.started" in event_names
        assert "mesh.run.dry_run" in event_names

    def test_mesh_run_nonexistent_component_fails(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh run on an unknown component returns non-zero exit."""
        result = cli_runner.invoke(
            cli_app,
            ["mesh", "run", "nonexistent_comp", "--dir", str(tmp_path), "--json"],
        )
        assert result.exit_code != 0

    def test_mesh_build_nonexistent_component_fails(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh build on an unknown component returns non-zero exit."""
        result = cli_runner.invoke(
            cli_app,
            ["mesh", "build", "nonexistent_comp", "--dir", str(tmp_path), "--json"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# System CLI E2E
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestSystemCLIE2E:
    """End-to-end system CLI scenarios."""

    def test_system_list_returns_json(self, cli_runner, cli_app) -> None:
        """system list --json returns a parseable JSON payload."""
        result = cli_runner.invoke(cli_app, ["system", "list", "--json"])
        assert result.exit_code == 0
        payloads = parse_json_lines(result.output)
        assert len(payloads) >= 1
        assert "systems" in payloads[0]

    def test_system_info_unknown_exits_nonzero(self, cli_runner, cli_app) -> None:
        """system info on an unknown system must fail."""
        result = cli_runner.invoke(
            cli_app, ["system", "info", "totally_unknown_sys_e2e", "--json"]
        )
        assert result.exit_code != 0

    def test_schema_export(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """schema export writes a JSON file."""
        out = tmp_path / "schema.json"
        result = cli_runner.invoke(cli_app, ["schema", "export", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# Plugin CLI E2E
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestPluginCLIE2E:
    """End-to-end plugin CLI scenarios."""

    def test_plugin_list_returns_readers_writers(self, cli_runner, cli_app) -> None:
        """plugin list --json payload contains readers and writers keys."""
        result = cli_runner.invoke(cli_app, ["plugin", "list", "--json"])
        assert result.exit_code == 0
        payloads = parse_json_lines(result.output)
        assert len(payloads) >= 1
        payload = payloads[0]
        assert "readers" in payload
        assert "writers" in payload

    def test_telemetry_status(self, cli_runner, cli_app) -> None:
        """telemetry status --json returns a valid payload."""
        result = cli_runner.invoke(cli_app, ["telemetry", "status", "--json"])
        assert result.exit_code == 0
        payloads = parse_json_lines(result.output)
        assert len(payloads) >= 1
