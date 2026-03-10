"""Dynamic autocompletion functions for aptdata CLI commands."""

from __future__ import annotations


def complete_system_names(incomplete: str) -> list[str]:
    """Return registered system names matching *incomplete*."""
    try:
        from aptdata.plugins import registry  # noqa: PLC0415

        return [n for n in registry.list_systems() if n.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []


def complete_reader_names(incomplete: str) -> list[str]:
    """Return registered reader plugin names matching *incomplete*."""
    try:
        from aptdata.plugins import plugin_manager  # noqa: PLC0415

        return [n for n in plugin_manager.list_readers() if n.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []


def complete_writer_names(incomplete: str) -> list[str]:
    """Return registered writer plugin names matching *incomplete*."""
    try:
        from aptdata.plugins import plugin_manager  # noqa: PLC0415

        return [n for n in plugin_manager.list_writers() if n.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []


def complete_plugin_names(incomplete: str) -> list[str]:
    """Return all registered plugin names (readers + writers) matching *incomplete*."""
    return sorted(
        set(complete_reader_names(incomplete)) | set(complete_writer_names(incomplete))
    )


def complete_env_names(incomplete: str) -> list[str]:
    """Return common environment names matching *incomplete*."""
    envs = ["dev", "staging", "prod", "test", "local"]
    return [e for e in envs if e.startswith(incomplete)]


def complete_template_names(incomplete: str) -> list[str]:
    """Return scaffold template names matching *incomplete*."""
    try:
        from aptdata.cli.scaffold import TEMPLATE_NAMES  # noqa: PLC0415

        return [t for t in TEMPLATE_NAMES if t.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []
