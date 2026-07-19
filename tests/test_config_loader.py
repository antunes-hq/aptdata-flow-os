"""Tests for the ``.aptdata/`` dotdir loader (ADR-002 §2.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aptdata.config.loader import (
    APTDATA_DIR_NAME,
    LEGACY_TO_DOTDIR,
    SCHEMA_FILES,
    ProjectConfig,
    ProjectNotFoundError,
    detect_legacy_files,
    load_default_mode,
    load_yaml_file,
    locate_project,
    locate_project_optional,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """A tmp dir with a ``.aptdata/`` dotdir and the three core files."""
    root = tmp_path / "myproj"
    aptdata = root / APTDATA_DIR_NAME
    aptdata.mkdir(parents=True)
    (aptdata / "system.yaml").write_text("system: {id: default}\n", encoding="utf-8")
    (aptdata / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
    (aptdata / "config.yaml").write_text("metadata: {}\n", encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# ProjectConfig
# ---------------------------------------------------------------------------


class TestProjectConfig:
    def test_paths_are_derived_from_aptdata_dir(self, project_root: Path):
        cfg = ProjectConfig(
            root=project_root, aptdata_dir=project_root / APTDATA_DIR_NAME
        )
        assert cfg.system_yaml == cfg.aptdata_dir / "system.yaml"
        assert cfg.agents_yaml == cfg.aptdata_dir / "agents.yaml"
        assert cfg.config_yaml == cfg.aptdata_dir / "config.yaml"
        assert cfg.schemas_dir == cfg.aptdata_dir / "schemas"

    def test_schema_for_returns_path_for_each_kind(self, project_root: Path):
        cfg = ProjectConfig(
            root=project_root, aptdata_dir=project_root / APTDATA_DIR_NAME
        )
        assert cfg.schema_for("agents") == cfg.schemas_dir / "agents.json"
        assert cfg.schema_for("system") == cfg.schemas_dir / "system.json"
        assert cfg.schema_for("config") == cfg.schemas_dir / "config.json"

    def test_exists_true_when_dotdir_has_any_file(self, project_root: Path):
        cfg = ProjectConfig(
            root=project_root, aptdata_dir=project_root / APTDATA_DIR_NAME
        )
        assert cfg.exists() is True

    def test_exists_false_when_dotdir_empty(self, tmp_path: Path):
        root = tmp_path / "empty"
        aptdata = root / APTDATA_DIR_NAME
        aptdata.mkdir(parents=True)
        cfg = ProjectConfig(root=root, aptdata_dir=aptdata)
        assert cfg.exists() is False

    def test_exists_false_when_dotdir_missing(self, tmp_path: Path):
        root = tmp_path / "no-dotdir"
        root.mkdir()
        cfg = ProjectConfig(root=root, aptdata_dir=root / APTDATA_DIR_NAME)
        assert cfg.exists() is False

    def test_is_frozen(self, project_root: Path):
        cfg = ProjectConfig(
            root=project_root, aptdata_dir=project_root / APTDATA_DIR_NAME
        )
        with pytest.raises(Exception):
            cfg.root = Path("/elsewhere")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# locate_project / locate_project_optional
# ---------------------------------------------------------------------------


class TestLocateProject:
    def test_finds_dotdir_at_root(self, project_root: Path):
        cfg = locate_project(project_root)
        assert cfg.root == project_root
        assert cfg.aptdata_dir.name == APTDATA_DIR_NAME

    def test_finds_dotdir_from_subdirectory(self, project_root: Path):
        nested = project_root / "src" / "deep" / "pkg"
        nested.mkdir(parents=True)
        cfg = locate_project(nested)
        assert cfg.root == project_root

    def test_finds_dotdir_when_passed_a_file(self, project_root: Path):
        nested = project_root / "sub"
        nested.mkdir()
        a_file = nested / "code.py"
        a_file.write_text("print('hi')\n", encoding="utf-8")
        cfg = locate_project(a_file)
        assert cfg.root == project_root

    def test_defaults_to_cwd(self, project_root: Path, monkeypatch: pytest.MonkeyPatch):
        # Change into the project root so CWD-based discovery works.
        monkeypatch.chdir(project_root)
        cfg = locate_project()
        assert cfg.root == project_root

    def test_raises_when_not_found(self, tmp_path: Path):
        # tmp_path has no .aptdata/ anywhere up the tree (its parents are /tmp).
        with pytest.raises(ProjectNotFoundError, match=APTDATA_DIR_NAME):
            locate_project(tmp_path)

    def test_optional_returns_none_when_not_found(self, tmp_path: Path):
        assert locate_project_optional(tmp_path) is None

    def test_optional_returns_config_when_found(self, project_root: Path):
        cfg = locate_project_optional(project_root)
        assert cfg is not None
        assert cfg.root == project_root


# ---------------------------------------------------------------------------
# Legacy detection
# ---------------------------------------------------------------------------


class TestLegacyDetection:
    def test_detect_legacy_files_finds_root_yamls(self, tmp_path: Path):
        (tmp_path / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
        (tmp_path / "aptdata.yaml").write_text("system: {id: x}\n", encoding="utf-8")
        (tmp_path / "config.yaml").write_text("metadata: {}\n", encoding="utf-8")

        found = detect_legacy_files(tmp_path)
        names = {Path(p).name for p in found}
        assert names == {"agents.yaml", "aptdata.yaml", "config.yaml"}

    def test_detect_legacy_files_empty_when_none(self, tmp_path: Path):
        assert detect_legacy_files(tmp_path) == {}

    def test_legacy_to_dotdir_mapping_known(self):
        # The mapping is the contract for --migrate; if it drifts, migrate breaks.
        assert LEGACY_TO_DOTDIR == {
            "aptdata.yaml": "system.yaml",
            "agents.yaml": "agents.yaml",
            "config.yaml": "config.yaml",
        }

    def test_schema_files_mapping_known(self):
        assert SCHEMA_FILES == {
            "system.yaml": "schemas/system.json",
            "agents.yaml": "schemas/agents.json",
            "config.yaml": "schemas/config.json",
        }


# ---------------------------------------------------------------------------
# load_yaml_file
# ---------------------------------------------------------------------------


class TestLoadYamlFile:
    def test_loads_mapping(self, tmp_path: Path):
        path = tmp_path / "f.yaml"
        path.write_text("key: value\nlist: [1, 2]\n", encoding="utf-8")
        assert load_yaml_file(path) == {"key": "value", "list": [1, 2]}

    def test_returns_empty_dict_for_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")
        assert load_yaml_file(path) == {}


# ---------------------------------------------------------------------------
# load_default_mode (ADR-002 §2.3)
# ---------------------------------------------------------------------------


class TestLoadDefaultMode:
    """PR3 — o loader expõe só o ``default_mode`` do agents.yaml sem validar
    specs inteiros (usado pelo CLI para resolver o ``--mode`` default)."""

    def test_returns_mode_when_present(self, tmp_path: Path):
        from aptdata.agents.modes import ExecutionMode

        path = tmp_path / "agents.yaml"
        path.write_text("default_mode: orchestrated\nagents: {}\n", encoding="utf-8")
        assert load_default_mode(path) is ExecutionMode.ORCHESTRATED

    def test_returns_none_when_field_absent(self, tmp_path: Path):
        path = tmp_path / "agents.yaml"
        path.write_text("agents: {}\n", encoding="utf-8")
        assert load_default_mode(path) is None

    def test_returns_none_when_file_missing(self, tmp_path: Path):
        assert load_default_mode(tmp_path / "nope.yaml") is None

    def test_returns_none_when_yaml_is_not_mapping(self, tmp_path: Path):
        path = tmp_path / "agents.yaml"
        path.write_text("- just\n- a\n- list\n", encoding="utf-8")
        assert load_default_mode(path) is None

    def test_raises_on_invalid_mode(self, tmp_path: Path):
        path = tmp_path / "agents.yaml"
        path.write_text("default_mode: bogus\nagents: {}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Unknown execution mode"):
            load_default_mode(path)

    def test_accepts_all_four_modes(self, tmp_path: Path):
        from aptdata.agents.modes import ExecutionMode

        for mode in ExecutionMode:
            path = tmp_path / f"{mode.value}.yaml"
            path.write_text(
                f"default_mode: {mode.value}\nagents: {{}}\n", encoding="utf-8"
            )
            assert load_default_mode(path) is mode
