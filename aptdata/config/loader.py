"""Project configuration loader for the ``.aptdata/`` dotdir (ADR-002 §2.2).

The ``.aptdata/`` directory is the **single source of truth** for a project's
declarative structure — versioned at the project root (alongside
``pyproject.toml``). It replaces the previously scattered ``aptdata.yaml`` /
``agents.yaml`` at the repo root with one canonical location:

::

    .aptdata/
    ├── system.yaml     # system manifest (was aptdata.yaml)
    ├── agents.yaml     # agent registry (was agents.yaml at root)
    ├── config.yaml     # declarative pipeline config (ParsedConfig)
    └── schemas/        # versioned JSON Schemas (generated, validated)

Discovery walks **up** the directory tree (like ``git`` does for
``.git/``): any subfolder of a project can call ``locate_project()``
and find the right ``.aptdata/``.

Per ADR-002 §4.1 (exceção Q6), migration is **immediate** — there is no
dual-read fallback to the legacy root-level files. ``aptdata init --migrate``
moves legacy files into ``.aptdata/``; once moved, only the dotdir is read.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

#: Name of the dotdir at the project root.
APTDATA_DIR_NAME = ".aptdata"

#: Files inside ``.aptdata/`` and their legacy root-level counterparts.
#: Used by ``aptdata init --migrate`` to know what to move.
LEGACY_TO_DOTDIR: dict[str, str] = {
    "aptdata.yaml": "system.yaml",
    "agents.yaml": "agents.yaml",
    "config.yaml": "config.yaml",
}

#: Schema artifacts (committed in ``.aptdata/schemas/``) per file.
SCHEMA_FILES: dict[str, str] = {
    "system.yaml": "schemas/system.json",
    "agents.yaml": "schemas/agents.json",
    "config.yaml": "schemas/config.json",
}


class ProjectConfig(BaseModel):
    """Resolved paths for a located ``.aptdata/`` project.

    Attributes
    ----------
    root:
        The project root (parent of the ``.aptdata/`` directory).
    aptdata_dir:
        The ``.aptdata/`` directory itself.
    system_yaml:
        Path to ``.aptdata/system.yaml`` (the system manifest).
    agents_yaml:
        Path to ``.aptdata/agents.yaml`` (the agent registry).
    config_yaml:
        Path to ``.aptdata/config.yaml`` (the declarative pipeline config).
    """

    model_config = ConfigDict(frozen=True)

    root: Path
    aptdata_dir: Path

    @property
    def system_yaml(self) -> Path:
        return self.aptdata_dir / "system.yaml"

    @property
    def agents_yaml(self) -> Path:
        return self.aptdata_dir / "agents.yaml"

    @property
    def config_yaml(self) -> Path:
        return self.aptdata_dir / "config.yaml"

    @property
    def schemas_dir(self) -> Path:
        return self.aptdata_dir / "schemas"

    def schema_for(self, kind: str) -> Path:
        """Return the path to the JSON Schema for ``agents``/``system``/``config``."""
        return self.schemas_dir / f"{kind}.json"

    def exists(self) -> bool:
        """Return ``True`` if the dotdir and at least one of its files exist."""
        return self.aptdata_dir.is_dir() and (
            self.system_yaml.exists()
            or self.agents_yaml.exists()
            or self.config_yaml.exists()
        )


class ProjectNotFoundError(FileNotFoundError):
    """Raised when no ``.aptdata/`` directory can be found walking up the tree."""


def locate_project(start: Path | str | None = None) -> ProjectConfig:
    """Locate the ``.aptdata/`` directory by walking up from *start*.

    Mirrors the behaviour of ``git`` for ``.git/``: starts at *start* (or
    the current working directory when omitted) and ascends until it finds
    a directory containing ``.aptdata/``.

    Parameters
    ----------
    start:
        Directory to start the search from. Defaults to the current working
        directory.

    Returns
    -------
    ProjectConfig
        Resolved paths for the located project.

    Raises
    ------
    ProjectNotFoundError
        When no ``.aptdata/`` directory is found between *start* and the
        filesystem root.
    """
    start_path = Path(start or Path.cwd()).resolve()
    if not start_path.is_dir():
        # If a file was passed, start from its parent.
        start_path = start_path.parent if start_path.exists() else Path.cwd()

    candidate = start_path
    while True:
        aptdata_dir = candidate / APTDATA_DIR_NAME
        if aptdata_dir.is_dir():
            return ProjectConfig(root=candidate, aptdata_dir=aptdata_dir)
        if candidate.parent == candidate:
            # Reached the filesystem root.
            raise ProjectNotFoundError(
                f"No '{APTDATA_DIR_NAME}/' directory found walking up from "
                f"{start_path}. Run 'aptdata init' to create one, or "
                "'aptdata init --migrate' if you have legacy aptdata.yaml/"
                "agents.yaml at the project root."
            )
        candidate = candidate.parent


def locate_project_optional(start: Path | str | None = None) -> ProjectConfig | None:
    """Like :func:`locate_project` but returns ``None`` instead of raising.

    Useful for CLI commands that want to fall back gracefully when invoked
    outside a project (e.g. ``aptdata plugins list`` doesn't need a project).
    """
    try:
        return locate_project(start)
    except ProjectNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Legacy migration helpers (used by ``aptdata init --migrate``)
# ---------------------------------------------------------------------------


def detect_legacy_files(root: Path) -> dict[str, Path]:
    """Find legacy root-level files that should migrate into ``.aptdata/``.

    Returns a ``{legacy_path: dotdir_relative_path}`` mapping for every
    legacy file that exists at *root*.
    """
    found: dict[str, Path] = {}
    for legacy_name in LEGACY_TO_DOTDIR:
        legacy_path = root / legacy_name
        if legacy_path.is_file():
            found[str(legacy_path)] = legacy_path
    return found


def load_yaml_file(path: Path) -> Any:
    """Load a YAML file as a plain Python object (dict / list / scalars).

    Centralised so the loader and the migration logic share one reader.
    """
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


__all__ = [
    "APTDATA_DIR_NAME",
    "LEGACY_TO_DOTDIR",
    "ProjectConfig",
    "ProjectNotFoundError",
    "SCHEMA_FILES",
    "detect_legacy_files",
    "load_yaml_file",
    "locate_project",
    "locate_project_optional",
]
