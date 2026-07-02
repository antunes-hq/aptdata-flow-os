"""Tests for scaffold templates — verifies generated file structures."""

from __future__ import annotations

from pathlib import Path

from aptdata.cli.scaffold import (
    TEMPLATE_NAMES,
    _scaffold_dashboard,  # noqa: PLC2701
    _scaffold_data_quality_test,  # noqa: PLC2701
    _scaffold_docker_compose_app,  # noqa: PLC2701
    _scaffold_hello_world,  # noqa: PLC2701
    _scaffold_job_wheel,  # noqa: PLC2701
    _scaffold_medallion,  # noqa: PLC2701
    _scaffold_rag_ingestion,  # noqa: PLC2701
    _scaffold_viz_panel,  # noqa: PLC2701
)

# ---------------------------------------------------------------------------
# Template name registry
# ---------------------------------------------------------------------------


class TestTemplateNames:
    def test_all_templates_present(self) -> None:
        assert "hello-world" in TEMPLATE_NAMES
        assert "medallion" in TEMPLATE_NAMES
        assert "rag-ingestion" in TEMPLATE_NAMES
        assert "data-quality-test" in TEMPLATE_NAMES
        assert "job-wheel" in TEMPLATE_NAMES
        assert "docker-compose-app" in TEMPLATE_NAMES
        assert "viz-panel" in TEMPLATE_NAMES
        assert "dashboard" in TEMPLATE_NAMES

    def test_template_count(self) -> None:
        assert len(TEMPLATE_NAMES) == 8


# ---------------------------------------------------------------------------
# hello-world template
# ---------------------------------------------------------------------------


class TestHelloWorldScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "my_project"
        project_dir.mkdir()
        _scaffold_hello_world("my_project", project_dir)

        assert (project_dir / "main.py").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "data" / "selecao_brasileira.json").exists()
        assert (project_dir / "output").is_dir()

    def test_requirements_contains_pandas(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_hello_world("proj", project_dir)
        content = (project_dir / "requirements.txt").read_text()
        assert "pandas" in content

    def test_main_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myproj"
        project_dir.mkdir()
        _scaffold_hello_world("myproj", project_dir)
        content = (project_dir / "main.py").read_text()
        assert "myproj" in content

    def test_readme_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myproj"
        project_dir.mkdir()
        _scaffold_hello_world("myproj", project_dir)
        content = (project_dir / "README.md").read_text()
        assert "myproj" in content


# ---------------------------------------------------------------------------
# medallion template
# ---------------------------------------------------------------------------


class TestMedallionScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "lakehouse"
        project_dir.mkdir()
        _scaffold_medallion("lakehouse", project_dir)

        assert (project_dir / "bronze.py").exists()
        assert (project_dir / "silver.py").exists()
        assert (project_dir / "gold.py").exists()
        assert (project_dir / "aptdata.yaml").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data").is_dir()
        assert (project_dir / "output").is_dir()

    def test_yaml_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_medallion("proj", project_dir)
        content = (project_dir / "aptdata.yaml").read_text()
        assert "proj" in content
        assert "medallion" in content

    def test_silver_references_transformer(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_medallion("proj", project_dir)
        silver = (project_dir / "silver.py").read_text()
        assert "PandasTransformer" in silver

    def test_silver_references_quality(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_medallion("proj", project_dir)
        silver = (project_dir / "silver.py").read_text()
        assert "QualityValidator" in silver

    def test_requirements_contains_pandas(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_medallion("proj", project_dir)
        content = (project_dir / "requirements.txt").read_text()
        assert "pandas" in content


# ---------------------------------------------------------------------------
# rag-ingestion template
# ---------------------------------------------------------------------------


class TestRagIngestionScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "rag_proj"
        project_dir.mkdir()
        _scaffold_rag_ingestion("rag_proj", project_dir)

        assert (project_dir / "pipeline.py").exists()
        assert (project_dir / "aptdata.yaml").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data").is_dir()

    def test_pipeline_contains_workflow(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_rag_ingestion("proj", project_dir)
        content = (project_dir / "pipeline.py").read_text()
        assert "Workflow" in content

    def test_pipeline_has_four_steps(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_rag_ingestion("proj", project_dir)
        content = (project_dir / "pipeline.py").read_text()
        assert "extract" in content
        assert "chunk" in content
        assert "embed" in content
        assert "load_to_vector_store" in content

    def test_yaml_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_rag_ingestion("proj", project_dir)
        content = (project_dir / "aptdata.yaml").read_text()
        assert "proj" in content
        assert "rag-ingestion" in content


# ---------------------------------------------------------------------------
# data-quality-test template
# ---------------------------------------------------------------------------


class TestDataQualityTestScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "dq_proj"
        project_dir.mkdir()
        _scaffold_data_quality_test("dq_proj", project_dir)

        assert (project_dir / "quality_pipeline.py").exists()
        assert (project_dir / "aptdata.yaml").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data").is_dir()

    def test_pipeline_contains_schema_contract(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_data_quality_test("proj", project_dir)
        content = (project_dir / "quality_pipeline.py").read_text()
        assert "SchemaContract" in content

    def test_pipeline_contains_expectations(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_data_quality_test("proj", project_dir)
        content = (project_dir / "quality_pipeline.py").read_text()
        assert "ExpectColumnToNotBeNull" in content

    def test_yaml_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_data_quality_test("proj", project_dir)
        content = (project_dir / "aptdata.yaml").read_text()
        assert "proj" in content
        assert "data-quality-test" in content

    def test_readme_mentions_enforcement_modes(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_data_quality_test("proj", project_dir)
        content = (project_dir / "README.md").read_text()
        assert "ABORT" in content
        assert "WARN" in content


# ---------------------------------------------------------------------------
# CLI integration — scaffold command with --template flag
# ---------------------------------------------------------------------------


class TestScaffoldCLITemplate:
    def test_hello_world_default(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app, ["scaffold", "myproject", "--output", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "main.py").exists()

    def test_medallion_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "scaffold",
                "myproject",
                "--output",
                str(tmp_path),
                "--template",
                "medallion",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "bronze.py").exists()
        assert (tmp_path / "myproject" / "silver.py").exists()
        assert (tmp_path / "myproject" / "gold.py").exists()

    def test_rag_ingestion_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "scaffold",
                "ragproject",
                "--output",
                str(tmp_path),
                "--template",
                "rag-ingestion",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "ragproject" / "pipeline.py").exists()

    def test_data_quality_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "scaffold",
                "dqproject",
                "--output",
                str(tmp_path),
                "--template",
                "data-quality-test",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "dqproject" / "quality_pipeline.py").exists()

    def test_unknown_template_exits_with_error(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "scaffold",
                "proj",
                "--output",
                str(tmp_path),
                "--template",
                "nonexistent",
            ],
        )
        assert result.exit_code != 0

    def test_job_wheel_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", "myjob", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        assert result.exit_code == 0
        assert (tmp_path / "myjob" / "src" / "myjob" / "job.py").exists()

    def test_docker_compose_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "scaffold",
                "myapp",
                "--output",
                str(tmp_path),
                "--template",
                "docker-compose-app",
            ],
        )
        assert result.exit_code == 0
        assert (tmp_path / "myapp" / "docker-compose.yml").exists()


# ---------------------------------------------------------------------------
# job-wheel template
# ---------------------------------------------------------------------------


class TestJobWheelScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myjob"
        project_dir.mkdir()
        _scaffold_job_wheel("myjob", project_dir)

        assert (project_dir / "src" / "myjob" / "__init__.py").exists()
        assert (project_dir / "src" / "myjob" / "job.py").exists()
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "mesh.yaml").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "README.md").exists()

    def test_pyproject_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myjob"
        project_dir.mkdir()
        _scaffold_job_wheel("myjob", project_dir)
        content = (project_dir / "pyproject.toml").read_text()
        assert "myjob" in content
        assert "wheel" in content

    def test_job_contains_main_function(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myjob"
        project_dir.mkdir()
        _scaffold_job_wheel("myjob", project_dir)
        content = (project_dir / "src" / "myjob" / "job.py").read_text()
        assert "def main" in content
        assert "def run" in content

    def test_mesh_yaml_type_is_job_wheel(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myjob"
        project_dir.mkdir()
        _scaffold_job_wheel("myjob", project_dir)
        content = (project_dir / "mesh.yaml").read_text()
        assert "job-wheel" in content
        assert "myjob" in content

    def test_readme_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myjob"
        project_dir.mkdir()
        _scaffold_job_wheel("myjob", project_dir)
        content = (project_dir / "README.md").read_text()
        assert "myjob" in content


# ---------------------------------------------------------------------------
# docker-compose-app template
# ---------------------------------------------------------------------------


class TestDockerComposeAppScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myapp"
        project_dir.mkdir()
        _scaffold_docker_compose_app("myapp", project_dir)

        assert (project_dir / "app.py").exists()
        assert (project_dir / "Dockerfile").exists()
        assert (project_dir / "docker-compose.yml").exists()
        assert (project_dir / "mesh.yaml").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data").is_dir()

    def test_docker_compose_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myapp"
        project_dir.mkdir()
        _scaffold_docker_compose_app("myapp", project_dir)
        content = (project_dir / "docker-compose.yml").read_text()
        assert "myapp" in content

    def test_app_contains_main_function(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myapp"
        project_dir.mkdir()
        _scaffold_docker_compose_app("myapp", project_dir)
        content = (project_dir / "app.py").read_text()
        assert "def main" in content

    def test_dockerfile_uses_python(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myapp"
        project_dir.mkdir()
        _scaffold_docker_compose_app("myapp", project_dir)
        content = (project_dir / "Dockerfile").read_text()
        assert "python" in content.lower()

    def test_mesh_yaml_type_is_docker_compose(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "myapp"
        project_dir.mkdir()
        _scaffold_docker_compose_app("myapp", project_dir)
        content = (project_dir / "mesh.yaml").read_text()
        assert "docker-compose-app" in content
        assert "myapp" in content


# ---------------------------------------------------------------------------
# mesh CLI command
# ---------------------------------------------------------------------------


class TestMeshCLI:
    def test_mesh_list_no_components(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["mesh", "list", "--dir", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output.strip())
        assert data["count"] == 0

    def test_mesh_list_finds_job_wheel_component(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        # Create a job-wheel project
        runner = CliRunner()
        runner.invoke(
            app,
            ["scaffold", "myjob", "--output", str(tmp_path), "--template", "job-wheel"],
        )

        result = runner.invoke(app, ["mesh", "list", "--dir", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output.strip())
        assert data["count"] == 1
        assert data["components"][0]["type"] == "job-wheel"

    def test_mesh_list_finds_docker_compose_component(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "myapp",
                "--output",
                str(tmp_path),
                "--template",
                "docker-compose-app",
            ],
        )

        result = runner.invoke(app, ["mesh", "list", "--dir", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output.strip())
        assert data["count"] == 1
        assert data["components"][0]["type"] == "docker-compose-app"

    def test_mesh_run_dry_run_job_wheel(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            ["scaffold", "myjob", "--output", str(tmp_path), "--template", "job-wheel"],
        )

        result = runner.invoke(
            app,
            ["mesh", "run", "myjob", "--dir", str(tmp_path), "--dry-run", "--json"],
        )
        assert result.exit_code == 0
        import json

        lines = [line for line in result.output.strip().splitlines() if line]
        events = [json.loads(line) for line in lines]
        event_names = [e.get("event") for e in events]
        assert "mesh.run.dry_run" in event_names

    def test_mesh_run_dry_run_docker_compose(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "myapp",
                "--output",
                str(tmp_path),
                "--template",
                "docker-compose-app",
            ],
        )

        result = runner.invoke(
            app,
            ["mesh", "run", "myapp", "--dir", str(tmp_path), "--dry-run", "--json"],
        )
        assert result.exit_code == 0
        import json

        lines = [line for line in result.output.strip().splitlines() if line]
        events = [json.loads(line) for line in lines]
        event_names = [e.get("event") for e in events]
        assert "mesh.run.dry_run" in event_names

    def test_mesh_run_unknown_component_exits_with_error(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mesh", "run", "nonexistent", "--dir", str(tmp_path), "--json"],
        )
        assert result.exit_code != 0

    def test_mesh_list_no_components_rich_mode(self, tmp_path: Path) -> None:
        """mesh list without --json emits a warning when no components found."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["mesh", "list", "--dir", str(tmp_path)])
        assert result.exit_code == 0

    def test_mesh_list_finds_component_rich_mode(self, tmp_path: Path) -> None:
        """mesh list without --json renders a Rich table when components exist."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "richjob",
                "--output",
                str(tmp_path),
                "--template",
                "job-wheel",
            ],
        )
        result = runner.invoke(app, ["mesh", "list", "--dir", str(tmp_path)])
        assert result.exit_code == 0

    def test_mesh_run_dry_run_rich_mode(self, tmp_path: Path) -> None:
        """mesh run --dry-run without --json prints a plain-text description."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "richjob2",
                "--output",
                str(tmp_path),
                "--template",
                "job-wheel",
            ],
        )
        result = runner.invoke(
            app,
            ["mesh", "run", "richjob2", "--dir", str(tmp_path), "--dry-run"],
        )
        assert result.exit_code == 0

    def test_mesh_run_unknown_component_rich_mode(self, tmp_path: Path) -> None:
        """mesh run on unknown component without --json exits non-zero."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mesh", "run", "ghost", "--dir", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_mesh_build_component_not_found_rich_mode(self, tmp_path: Path) -> None:
        """mesh build on unknown component without --json exits non-zero."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mesh", "build", "ghost_component", "--dir", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_mesh_build_component_not_found_json_mode(self, tmp_path: Path) -> None:
        """mesh build on unknown component with --json emits mesh.error event."""
        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["mesh", "build", "ghost_component", "--dir", str(tmp_path), "--json"],
        )
        assert result.exit_code != 0
        import json

        lines = [line for line in result.output.strip().splitlines() if line]
        events = [json.loads(line) for line in lines]
        event_names = [e.get("event") for e in events]
        assert "mesh.error" in event_names

    def test_mesh_build_job_wheel_json_mode(self, tmp_path: Path) -> None:
        """mesh build job-wheel component succeeds (mocked subprocess) and emits
        build events."""
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "buildme",
                "--output",
                str(tmp_path),
                "--template",
                "job-wheel",
            ],
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0

        with patch(
            "aptdata.cli.commands.mesh_cmd.subprocess.run", return_value=mock_proc
        ):
            result = runner.invoke(
                app,
                ["mesh", "build", "buildme", "--dir", str(tmp_path), "--json"],
            )
        assert result.exit_code == 0
        import json

        lines = [line for line in result.output.strip().splitlines() if line]
        events = [json.loads(line) for line in lines]
        event_names = [e.get("event") for e in events]
        assert "mesh.build.started" in event_names
        assert "mesh.build.completed" in event_names

    def test_mesh_build_job_wheel_rich_mode(self, tmp_path: Path) -> None:
        """mesh build job-wheel component succeeds (mocked subprocess) in rich mode."""
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "buildme2",
                "--output",
                str(tmp_path),
                "--template",
                "job-wheel",
            ],
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0

        with patch(
            "aptdata.cli.commands.mesh_cmd.subprocess.run", return_value=mock_proc
        ):
            result = runner.invoke(
                app,
                ["mesh", "build", "buildme2", "--dir", str(tmp_path)],
            )
        assert result.exit_code == 0

    def test_mesh_run_job_wheel_with_mock(self, tmp_path: Path) -> None:
        """mesh run job-wheel component succeeds with mocked subprocess."""
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from aptdata.cli.app import app

        runner = CliRunner()
        runner.invoke(
            app,
            [
                "scaffold",
                "runjob",
                "--output",
                str(tmp_path),
                "--template",
                "job-wheel",
            ],
        )

        mock_proc = MagicMock()
        mock_proc.returncode = 0

        with patch(
            "aptdata.cli.commands.mesh_cmd.subprocess.run", return_value=mock_proc
        ):
            result = runner.invoke(
                app,
                ["mesh", "run", "runjob", "--dir", str(tmp_path), "--json"],
            )
        assert result.exit_code == 0
        import json

        lines = [line for line in result.output.strip().splitlines() if line]
        events = [json.loads(line) for line in lines]
        event_names = [e.get("event") for e in events]
        assert "mesh.run.started" in event_names
        assert "mesh.run.completed" in event_names


# ---------------------------------------------------------------------------
# design-system templates (viz-panel / dashboard)
# ---------------------------------------------------------------------------


class TestVizPanelScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        d = tmp_path / "meupainel"
        d.mkdir()
        _scaffold_viz_panel("meupainel", d)
        assert (d / "index.html").exists()
        assert (d / "assets" / "tokens.css").exists()
        assert (d / "assets" / "components.css").exists()
        assert (d / "README.md").exists()

    def test_index_is_thin_client(self, tmp_path: Path) -> None:
        d = tmp_path / "p"
        d.mkdir()
        _scaffold_viz_panel("p", d)
        html = (d / "index.html").read_text(encoding="utf-8")
        assert "assets/tokens.css" in html
        assert "/api/agents" in html and "/api/health" in html
        # zero build / zero CDN: nenhum script externo
        assert "<script src=\"http" not in html

    def test_tokens_have_light_and_dark_modes(self, tmp_path: Path) -> None:
        d = tmp_path / "p"
        d.mkdir()
        _scaffold_viz_panel("p", d)
        css = (d / "assets" / "tokens.css").read_text(encoding="utf-8")
        assert "--surface-1" in css and "--series-1" in css
        assert "prefers-color-scheme: dark" in css

    def test_status_badges_carry_label_not_only_color(self, tmp_path: Path) -> None:
        d = tmp_path / "p"
        d.mkdir()
        _scaffold_viz_panel("p", d)
        html = (d / "index.html").read_text(encoding="utf-8")
        # status nunca é só cor: o texto do estado acompanha o dot
        assert "badge" in html and "statusLabel" in html


class TestDashboardScaffold:
    def test_generates_expected_files(self, tmp_path: Path) -> None:
        d = tmp_path / "dash"
        d.mkdir()
        _scaffold_dashboard("dash", d)
        assert (d / "index.html").exists()
        assert (d / "data.json").exists()
        assert (d / "assets" / "tokens.css").exists()
        assert (d / "assets" / "components.css").exists()
        assert (d / "README.md").exists()

    def test_has_table_view_and_direct_labels(self, tmp_path: Path) -> None:
        # regra de relevo do validador: cores <3:1 exigem labels/tabela
        d = tmp_path / "dash"
        d.mkdir()
        _scaffold_dashboard("dash", d)
        html = (d / "index.html").read_text(encoding="utf-8")
        assert "<table" in html
        assert "tabular-nums" in (d / "assets" / "components.css").read_text(
            encoding="utf-8"
        )

    def test_chart_is_inline_svg_single_series(self, tmp_path: Path) -> None:
        d = tmp_path / "dash"
        d.mkdir()
        _scaffold_dashboard("dash", d)
        html = (d / "index.html").read_text(encoding="utf-8")
        assert "<svg" in html or "createElementNS" in html
        assert "<script src=\"http" not in html  # sem CDN


class TestDesignTokensSingleSource:
    def test_both_templates_project_identical_tokens(self, tmp_path: Path) -> None:
        """tokens.css é fonte única: os templates são projeções, não cópias."""
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        _scaffold_viz_panel("a", a)
        _scaffold_dashboard("b", b)
        assert (a / "assets" / "tokens.css").read_text(encoding="utf-8") == (
            b / "assets" / "tokens.css"
        ).read_text(encoding="utf-8")
