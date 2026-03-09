"""CLI sub-command packages for smart-data."""

from smart_data.cli.commands.system_cmd import system_app
from smart_data.cli.commands.plugin_cmd import plugin_app
from smart_data.cli.commands.config_cmd import config_app
from smart_data.cli.commands.telemetry_cmd import telemetry_app
from smart_data.cli.commands.mesh_cmd import mesh_app

__all__ = ["system_app", "plugin_app", "config_app", "telemetry_app", "mesh_app"]
