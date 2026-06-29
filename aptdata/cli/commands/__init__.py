"""CLI sub-command packages for aptdata."""

from aptdata.cli.commands.agents_cmd import agents_app
from aptdata.cli.commands.config_cmd import config_app
from aptdata.cli.commands.mesh_cmd import mesh_app
from aptdata.cli.commands.plugin_cmd import plugin_app
from aptdata.cli.commands.system_cmd import system_app
from aptdata.cli.commands.telemetry_cmd import telemetry_app

__all__ = [
    "agents_app",
    "system_app",
    "plugin_app",
    "config_app",
    "telemetry_app",
    "mesh_app",
]
