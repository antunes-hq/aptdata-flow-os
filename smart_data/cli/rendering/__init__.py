"""Rich rendering layer for smart-data CLI."""

from smart_data.cli.rendering.console import SmartConsole
from smart_data.cli.rendering.tables import (
    systems_table,
    plugins_table,
    plugin_schema_table,
    config_summary_table,
    telemetry_status_table,
)
from smart_data.cli.rendering.panels import (
    system_detail_panel,
    flow_tree,
    yaml_preview,
    component_panel,
)
from smart_data.cli.rendering.logger import setup_rich_logging

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
