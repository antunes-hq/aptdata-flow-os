"""Rich rendering layer for aptdata CLI."""

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.tables import (
    systems_table,
    plugins_table,
    plugin_schema_table,
    config_summary_table,
    telemetry_status_table,
)
from aptdata.cli.rendering.panels import (
    system_detail_panel,
    flow_tree,
    yaml_preview,
    component_panel,
)
from aptdata.cli.rendering.logger import setup_rich_logging

__all__ = [
    "SmartConsole",
    "systems_table",
    "plugins_table",
    "plugin_schema_table",
    "config_summary_table",
    "telemetry_status_table",
    "system_detail_panel",
    "flow_tree",
    "yaml_preview",
    "component_panel",
    "setup_rich_logging",
]
