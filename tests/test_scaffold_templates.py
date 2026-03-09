"""Tests for scaffold templates — verifies generated file structures."""

from __future__ import annotations

from pathlib import Path

import pytest

from smart_data.cli.scaffold import _scaffold_data_quality_test  # noqa: PLC2701
from smart_data.cli.scaffold import _scaffold_hello_world  # noqa: PLC2701
from smart_data.cli.scaffold import _scaffold_medallion  # noqa: PLC2701
from smart_data.cli.scaffold import _scaffold_rag_ingestion  # noqa: PLC2701
from smart_data.cli.scaffold import TEMPLATE_NAMES


# ---------------------------------------------------------------------------
# Template name registry
# ---------------------------------------------------------------------------


class TestTemplateNames:
    def test_all_templates_present(self) -> None:
        assert "hello-world" in TEMPLATE_NAMES
        assert "medallion" in TEMPLATE_NAMES
        assert "rag-ingestion" in TEMPLATE_NAMES
        assert "data-quality-test" in TEMPLATE_NAMES

    def test_template_count(self) -> None:
        assert len(TEMPLATE_NAMES) == 4


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
        assert (project_dir / "smart-data.yaml").exists()
        assert (project_dir / "requirements.txt").exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "data").is_dir()
        assert (project_dir / "output").is_dir()

    def test_yaml_contains_project_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _scaffold_medallion("proj", project_dir)
        content = (project_dir / "smart-data.yaml").read_text()
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
        assert (project_dir / "smart-data.yaml").exists()
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
        content = (project_dir / "smart-data.yaml").read_text()
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
        assert (project_dir / "smart-data.yaml").exists()
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
        content = (project_dir / "smart-data.yaml").read_text()
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

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(app, ["scaffold", "myproject", "--output", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "main.py").exists()

    def test_medallion_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", "myproject", "--output", str(tmp_path), "--template", "medallion"],
        )
        assert result.exit_code == 0
        assert (tmp_path / "myproject" / "bronze.py").exists()
        assert (tmp_path / "myproject" / "silver.py").exists()
        assert (tmp_path / "myproject" / "gold.py").exists()

    def test_rag_ingestion_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", "ragproject", "--output", str(tmp_path), "--template", "rag-ingestion"],
        )
        assert result.exit_code == 0
        assert (tmp_path / "ragproject" / "pipeline.py").exists()

    def test_data_quality_template(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", "dqproject", "--output", str(tmp_path), "--template", "data-quality-test"],
        )
        assert result.exit_code == 0
        assert (tmp_path / "dqproject" / "quality_pipeline.py").exists()

    def test_unknown_template_exits_with_error(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner

        from smart_data.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", "proj", "--output", str(tmp_path), "--template", "nonexistent"],
        )
        assert result.exit_code != 0
