"""Integration tests — wire multiple aptdata components together.

These tests exercise real component interactions without mocking internals.
Each test is marked ``@pytest.mark.integration``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tests.conftest import assert_json_event


# ---------------------------------------------------------------------------
# Scaffold → mesh list → mesh run (dry-run) pipeline
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScaffoldMeshIntegration:
    """Scaffold a component then orchestrate it via mesh CLI."""

    def test_job_wheel_scaffold_and_mesh_list(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Scaffold a job-wheel project and verify mesh list finds it."""
        result = cli_runner.invoke(
            cli_app,
            ["scaffold", "integ_job", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["count"] == 1
        assert data["components"][0]["component"] == "integ_job"
        assert data["components"][0]["type"] == "job-wheel"

    def test_docker_compose_scaffold_and_mesh_list(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Scaffold a docker-compose-app and verify mesh list finds it."""
        result = cli_runner.invoke(
            cli_app,
            ["scaffold", "integ_app", "--output", str(tmp_path), "--template", "docker-compose-app"],
        )
        assert result.exit_code == 0, result.output

        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["count"] == 1
        assert data["components"][0]["type"] == "docker-compose-app"

    def test_mesh_run_dry_run_produces_event(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """mesh run --dry-run must emit a mesh.run.dry_run event."""
        cli_runner.invoke(
            cli_app,
            ["scaffold", "integ_job2", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        result = cli_runner.invoke(
            cli_app,
            ["mesh", "run", "integ_job2", "--dir", str(tmp_path), "--dry-run", "--json"],
        )
        assert result.exit_code == 0
        assert_json_event(result.output, "mesh.run.dry_run")

    def test_multiple_components_mesh_list(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """Scaffold two components and verify both appear in mesh list."""
        for name, template in [
            ("job_a", "job-wheel"),
            ("app_b", "docker-compose-app"),
        ]:
            cli_runner.invoke(
                cli_app,
                ["scaffold", name, "--output", str(tmp_path), "--template", template],
            )

        result = cli_runner.invoke(
            cli_app, ["mesh", "list", "--dir", str(tmp_path), "--json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output.strip())
        assert data["count"] == 2
        types = {c["type"] for c in data["components"]}
        assert types == {"job-wheel", "docker-compose-app"}


# ---------------------------------------------------------------------------
# Quality validator + expectations integration
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestQualityValidatorIntegration:
    """Run QualityValidator with real pandas DataFrames."""

    @pytest.fixture(autouse=True)
    def skip_without_pandas(self) -> None:
        pytest.importorskip("pandas")

    def test_abort_on_null(self, make_df) -> None:
        """ABORT enforcement raises ValueError on null data."""
        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            QualityValidator,
        )

        df = make_df(id=[1, None, 3], value=[10, 20, 30])
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("id")],
            enforcement=EnforcementMode.ABORT,
        )
        with pytest.raises(ValueError, match="quality validation failed"):
            validator.validate(df)

    def test_warn_on_null_passes_through(self, make_df) -> None:
        """WARN enforcement returns data even with null values."""
        import warnings

        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            QualityValidator,
        )

        df = make_df(id=[1, None, 3])
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("id")],
            enforcement=EnforcementMode.WARN,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = validator.validate(df)
        assert result is df
        assert len(w) > 0

    def test_tag_mode_annotates_metadata(self, make_dataset) -> None:
        """TAG enforcement attaches quality_report to dataset metadata."""
        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            QualityValidator,
        )

        ds = make_dataset([{"id": None}, {"id": 2}])
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("id")],
            enforcement=EnforcementMode.TAG,
        )
        result = validator.validate(ds)
        assert "quality_report" in result.schema_metadata
        assert result.schema_metadata["quality_report"]["passed"] is False

    def test_all_pass_returns_data_unchanged(self, make_df) -> None:
        """Validator returns same data object when all expectations pass."""
        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            QualityValidator,
        )

        df = make_df(id=[1, 2, 3])
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("id")],
            enforcement=EnforcementMode.ABORT,
        )
        result = validator.validate(df)
        assert result is df

    def test_multi_expectation_validation(self, make_df) -> None:
        """Multiple expectations are all evaluated before raising."""
        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            ExpectColumnValuesToBeUnique,
            QualityValidator,
        )

        df = make_df(id=[1, 1, 3], name=["a", "b", "c"])
        validator = QualityValidator(
            expectations=[
                ExpectColumnToNotBeNull("id"),
                ExpectColumnValuesToBeUnique("id"),
            ],
            enforcement=EnforcementMode.WARN,
            name="multi_check",
        )
        import warnings
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = validator.validate(df)
        assert result is df


# ---------------------------------------------------------------------------
# Transform + quality pipeline integration
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestTransformQualityPipelineIntegration:
    """Chain a PandasTransformer with a QualityValidator."""

    @pytest.fixture(autouse=True)
    def skip_without_pandas(self) -> None:
        pytest.importorskip("pandas")

    def test_clean_and_validate(self, make_df) -> None:
        """Transformer output passes through quality validation."""
        from aptdata.plugins.quality import (
            EnforcementMode,
            ExpectColumnToNotBeNull,
            QualityValidator,
        )
        from aptdata.plugins.transform import PandasTransformer

        def clean(df):
            return df.dropna()

        transformer = PandasTransformer("clean", clean)
        validator = QualityValidator(
            expectations=[ExpectColumnToNotBeNull("id")],
            enforcement=EnforcementMode.ABORT,
        )

        dirty = make_df(id=[1, None, 3], value=[10, 20, 30])
        cleaned = transformer.transform(dirty)
        # After dropping NaN, both remaining rows have non-null id
        result = validator.validate(cleaned)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Scaffold → file verification integration
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScaffoldFileIntegration:
    """Verify scaffolded project files contain expected content."""

    def test_hello_world_main_is_executable(self, scaffolded_project: Path) -> None:
        """The generated main.py can be imported without errors."""
        main_py = scaffolded_project / "main.py"
        assert main_py.exists()
        source = main_py.read_text()
        # Verify Python syntax by compiling
        compile(source, str(main_py), "exec")

    def test_medallion_yaml_is_valid(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """The medallion aptdata.yaml contains required keys."""
        import yaml  # type: ignore[import]

        cli_runner.invoke(
            cli_app,
            ["scaffold", "lh", "--output", str(tmp_path), "--template", "medallion"],
        )
        yaml_file = tmp_path / "lh" / "aptdata.yaml"
        assert yaml_file.exists()
        config = yaml.safe_load(yaml_file.read_text())
        assert config["project"] == "lh"
        assert config["template"] == "medallion"

    def test_job_wheel_pyproject_valid_toml(self, tmp_path: Path, cli_runner, cli_app) -> None:
        """The job-wheel pyproject.toml is syntactically valid."""
        if sys.version_info < (3, 11):
            pytest.skip("tomllib requires Python ≥ 3.11")
        import tomllib  # noqa: PLC0415

        cli_runner.invoke(
            cli_app,
            ["scaffold", "myjob", "--output", str(tmp_path), "--template", "job-wheel"],
        )
        toml_file = tmp_path / "myjob" / "pyproject.toml"
        assert toml_file.exists()
        config = tomllib.loads(toml_file.read_text())
        assert config["project"]["name"] == "myjob"
