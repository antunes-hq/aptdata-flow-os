"""Rich rendering layer for aptdata CLI."""

from aptdata.cli.rendering.console import SmartConsole
from aptdata.cli.rendering.logger import setup_rich_logging
from aptdata.cli.rendering.panels import (
    component_panel,
    flow_tree,
    system_detail_panel,
    yaml_preview,
)
from aptdata.cli.rendering.tables import (
    config_summary_table,
    plugin_schema_table,
    plugins_table,
    systems_table,
    telemetry_status_table,
)

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
