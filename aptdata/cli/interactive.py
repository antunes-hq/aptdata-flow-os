"""Interactive wizard for aptdata CLI.

Uses *questionary* (if available) for prompt-driven UX; falls back to
plain ``typer.prompt()`` when questionary is not installed.
"""

from __future__ import annotations

import typer

from aptdata.cli.rendering.console import SmartConsole

_console = SmartConsole(json_mode=False)

# ---------------------------------------------------------------------------
# questionary availability
# ---------------------------------------------------------------------------

try:
    import questionary  # type: ignore[import]

    _HAS_QUESTIONARY = True
except ModuleNotFoundError:
    _HAS_QUESTIONARY = False


def _select(message: str, choices: list[str]) -> str:
    """Prompt user to select from *choices*."""
    if _HAS_QUESTIONARY:
        answer = questionary.select(message, choices=choices).ask()
        return answer or choices[0]
    _console.print(f"\n{message}")
    for i, c in enumerate(choices, 1):
        _console.print(f"  {i}. {c}")
    idx_str = typer.prompt("Enter number", default="1")
    try:
        idx = int(idx_str) - 1
        return choices[max(0, min(idx, len(choices) - 1))]
    except ValueError:
        return choices[0]


def _text(message: str, default: str = "") -> str:
    """Prompt user for free text."""
    if _HAS_QUESTIONARY:
        answer = questionary.text(message, default=default).ask()
        return answer if answer is not None else default
    return typer.prompt(message, default=default)


def _confirm(message: str, default: bool = True) -> bool:
    """Prompt user for yes/no confirmation."""
    if _HAS_QUESTIONARY:
        answer = questionary.confirm(message, default=default).ask()
        return answer if answer is not None else default
    return typer.confirm(message, default=default)


# ---------------------------------------------------------------------------
# Wizard flows
# ---------------------------------------------------------------------------

_MAIN_MENU = [
    "🚀 Run a registered system",
    "📋 List systems / plugins",
    "🔍 Inspect a plugin",
    "📝 Config (validate / run YAML)",
    "🏗️  Scaffold a new project",
    "⚙️  Telemetry status",
    "❌ Exit",
]


def _wizard_run() -> None:
    """Guided wizard for running a registered system."""
    from aptdata.plugins import registry  # noqa: PLC0415

    names = registry.list_systems()
    if not names:
        _console.warning("No systems registered.")
        return

    name = _select("Select a system to run:", names)
    env = _select("Select environment:", ["dev", "staging", "prod"])
    dry_run = _confirm("Dry run (no execution)?", default=False)

    _console.rule(f"Running '{name}' [{env}]")
    system_cls = registry.get(name)
    if system_cls is None:
        _console.error(f"System '{name}' not found.")
        return

    try:
        with _console.spinner(f"Executing '{name}'..."):
            instance = system_cls(system_id=name)
            if not dry_run:
                instance.run()
        _console.success(f"System '{name}' completed.")
    except Exception as exc:  # noqa: BLE001
        _console.error(f"Execution failed: {exc}")


def _wizard_list() -> None:
    """Guided wizard for listing systems / plugins."""
    from aptdata.plugins import registry, plugin_manager  # noqa: PLC0415
    from aptdata.cli.rendering.tables import systems_table, plugins_table  # noqa: PLC0415

    choice = _select(
        "What to list?",
        ["Systems", "Readers", "Writers", "All plugins"],
    )

    if choice == "Systems":
        names = registry.list_systems()
        if names:
            _console.render(systems_table(names))
        else:
            _console.warning("No systems registered.")
    elif choice in ("Readers", "Writers", "All plugins"):
        plugins = plugin_manager.list_plugins()
        _console.render(plugins_table(plugins))


def _wizard_inspect() -> None:
    """Guided wizard for plugin inspection."""
    from aptdata.plugins import plugin_manager  # noqa: PLC0415
    from aptdata.cli.rendering.tables import plugin_schema_table  # noqa: PLC0415

    all_plugins = sorted(
        plugin_manager.list_readers() + plugin_manager.list_writers()
    )
    if not all_plugins:
        _console.warning("No plugins registered.")
        return

    name = _select("Select a plugin to inspect:", all_plugins)
    try:
        schema = plugin_manager.get_plugin_schema(name)
        _console.render(plugin_schema_table(schema))
    except KeyError as exc:
        _console.error(str(exc))


def _wizard_config() -> None:
    """Guided wizard for YAML config validation / run."""
    from aptdata.config.parser import YamlConfigParser  # noqa: PLC0415
    from aptdata.cli.rendering.panels import yaml_preview  # noqa: PLC0415
    from aptdata.cli.rendering.tables import config_summary_table  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    action = _select("Config action:", ["Load and validate", "Generate template"])

    if action == "Generate template":
        from aptdata.cli.commands.config_cmd import _STARTER_YAML  # noqa: PLC0415

        out_path_str = _text("Output path:", default="pipeline.yaml")
        out_path = Path(out_path_str)
        if out_path.exists():
            _console.warning(f"File '{out_path}' already exists.")
        else:
            out_path.write_text(_STARTER_YAML, encoding="utf-8")
            _console.success(f"Template written to '{out_path}'.")
        return

    path_str = _text("Path to YAML file:")
    if not path_str:
        _console.warning("No path provided.")
        return
    path = Path(path_str)
    if not path.exists():
        _console.error(f"File '{path}' not found.")
        return

    try:
        parser = YamlConfigParser()
        parsed = parser.parse_file(path)
        _console.success("Config is valid.")
        _console.render(config_summary_table(parsed))

        content = path.read_text(encoding="utf-8")
        if _confirm("Preview YAML?"):
            _console.render(yaml_preview(content))

        if _confirm("Run the system?", default=False):
            with _console.spinner("Running..."):
                parsed.system.run()
            _console.success("Done.")
    except Exception as exc:  # noqa: BLE001
        _console.error(f"Config error: {exc}")


def _wizard_scaffold() -> None:
    """Guided wizard for project scaffolding."""
    from aptdata.cli.scaffold import TEMPLATE_NAMES  # noqa: PLC0415

    name = _text("Project name:")
    if not name:
        _console.warning("No name provided.")
        return

    template = _select("Select template:", TEMPLATE_NAMES)
    output = _text("Output directory:", default=".")

    _console.rule(f"Scaffolding '{name}' [{template}]")
    try:
        from typer.testing import CliRunner  # noqa: PLC0415
        from aptdata.cli.app import app  # noqa: PLC0415

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["scaffold", name, "--template", template, "--output", output],
        )
        if result.exit_code == 0:
            _console.success(f"Project '{name}' created in '{output}/{name}'.")
        else:
            _console.error(f"Scaffold failed.\n{result.output}")
    except Exception as exc:  # noqa: BLE001
        _console.error(f"Scaffold error: {exc}")


def _wizard_telemetry() -> None:
    """Guided wizard for telemetry inspection."""
    from aptdata.cli.commands.telemetry_cmd import _get_telemetry_status  # noqa: PLC0415
    from aptdata.cli.rendering.tables import telemetry_status_table  # noqa: PLC0415

    status = _get_telemetry_status()
    _console.render(telemetry_status_table(status))

    if _confirm("Export telemetry as JSON?", default=False):
        import json  # noqa: PLC0415

        _console.print(json.dumps({"telemetry": status}, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def interactive_command() -> None:
    """Launch the interactive wizard for aptdata."""
    _console.rule("[bold cyan]aptdata interactive wizard[/bold cyan]")

    while True:
        choice = _select("What would you like to do?", _MAIN_MENU)

        if choice.startswith("🚀"):
            _wizard_run()
        elif choice.startswith("📋"):
            _wizard_list()
        elif choice.startswith("🔍"):
            _wizard_inspect()
        elif choice.startswith("📝"):
            _wizard_config()
        elif choice.startswith("🏗"):
            _wizard_scaffold()
        elif choice.startswith("⚙"):
            _wizard_telemetry()
        elif choice.startswith("❌"):
            _console.success("Goodbye!")
            break

        _console.rule()
