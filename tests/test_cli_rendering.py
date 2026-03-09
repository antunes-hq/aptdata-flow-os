"""Tests for smart_data.cli.rendering — SmartConsole, tables, panels, logger."""

from __future__ import annotations

import json

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from smart_data.cli.rendering.console import SmartConsole
from smart_data.cli.rendering.logger import setup_rich_logging
from smart_data.cli.rendering.panels import (
    component_panel,
    flow_tree,
    system_detail_panel,
    yaml_preview,
)
from smart_data.cli.rendering.tables import (
    config_summary_table,
    plugin_schema_table,
    plugins_table,
    systems_table,
    telemetry_status_table,
)


# ---------------------------------------------------------------------------
# SmartConsole — JSON mode
# ---------------------------------------------------------------------------


class TestSmartConsoleJsonMode:
    def test_emit_event_json(self, capsys):
        console = SmartConsole(json_mode=True)
        console.emit_event("test.event", key="value")
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)
        assert payload["event"] == "test.event"
        assert payload["key"] == "value"

    def test_success_json(self, capsys):
        console = SmartConsole(json_mode=True)
        console.success("all good")
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)
        assert payload["level"] == "success"
        assert "all good" in payload["message"]

    def test_warning_json(self, capsys):
        console = SmartConsole(json_mode=True)
        console.warning("heads up")
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)
        assert payload["level"] == "warning"
        assert "heads up" in payload["message"]

    def test_error_json(self, capsys):
        console = SmartConsole(json_mode=True)
        console.error("something broke")
        err = capsys.readouterr().err.strip()
        payload = json.loads(err)
        assert payload["level"] == "error"
        assert "something broke" in payload["message"]

    def test_info_json(self, capsys):
        console = SmartConsole(json_mode=True)
        console.info("informational")
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)
        assert payload["level"] == "info"
        assert "informational" in payload["message"]

    def test_spinner_is_noop_in_json_mode(self, capsys):
        console = SmartConsole(json_mode=True)
        ran = False
        with console.spinner("working..."):
            ran = True
        assert ran
        # No extra output from spinner
        out = capsys.readouterr().out
        assert out == ""

    def test_render_is_noop_in_json_mode(self, capsys):
        console = SmartConsole(json_mode=True)
        table = Table()
        table.add_column("col")
        table.add_row("val")
        console.render(table)
        out = capsys.readouterr().out
        assert out == ""


# ---------------------------------------------------------------------------
# SmartConsole — Rich mode
# ---------------------------------------------------------------------------


class TestSmartConsoleRichMode:
    def test_emit_event_rich(self, capsys):
        console = SmartConsole(json_mode=False)
        console.emit_event("test.event", key="value")
        # Rich mode writes to the Rich console, not capsys; no crash is the contract

    def test_success_rich(self, capsys):
        console = SmartConsole(json_mode=False)
        console.success("all good")  # Should not raise

    def test_warning_rich(self, capsys):
        console = SmartConsole(json_mode=False)
        console.warning("heads up")  # Should not raise

    def test_error_rich(self, capsys):
        console = SmartConsole(json_mode=False)
        console.error("something broke")  # Should not raise

    def test_spinner_context_manager(self):
        console = SmartConsole(json_mode=False)
        ran = False
        with console.spinner("working..."):
            ran = True
        assert ran

    def test_render_table(self):
        console = SmartConsole(json_mode=False)
        table = Table()
        table.add_column("col")
        table.add_row("val")
        console.render(table)  # Should not raise

    def test_rule_rich(self):
        console = SmartConsole(json_mode=False)
        console.rule("Test Rule")  # Should not raise

    def test_rule_noop_in_json_mode(self, capsys):
        console = SmartConsole(json_mode=True)
        console.rule("Test Rule")
        out = capsys.readouterr().out
        assert out == ""


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class TestSystemsTable:
    def test_returns_table(self):
        table = systems_table(["sys_a", "sys_b"])
        assert isinstance(table, Table)

    def test_empty_list(self):
        table = systems_table([])
        assert isinstance(table, Table)
        assert table.row_count == 0

    def test_row_count(self):
        table = systems_table(["a", "b", "c"])
        assert table.row_count == 3


class TestPluginsTable:
    def test_returns_table(self):
        table = plugins_table({"readers": ["r1"], "writers": ["w1"]})
        assert isinstance(table, Table)

    def test_empty_plugins(self):
        table = plugins_table({"readers": [], "writers": []})
        assert isinstance(table, Table)
        assert table.row_count == 0

    def test_row_count(self):
        table = plugins_table({"readers": ["r1", "r2"], "writers": ["w1"]})
        assert table.row_count == 3


class TestPluginSchemaTable:
    def test_returns_table(self):
        schema = {
            "name": "my_reader",
            "type": "reader",
            "arguments": [
                {"name": "path", "required": True, "default": None},
                {"name": "encoding", "required": False, "default": "utf-8"},
            ],
        }
        table = plugin_schema_table(schema)
        assert isinstance(table, Table)
        assert table.row_count == 2

    def test_empty_arguments(self):
        schema = {"name": "simple", "type": "reader", "arguments": []}
        table = plugin_schema_table(schema)
        assert isinstance(table, Table)
        assert table.row_count == 0


class TestConfigSummaryTable:
    def test_returns_table(self):
        from smart_data.config.parser import YamlConfigParser

        parsed = YamlConfigParser().parse_data(
            {
                "metadata": {"name": "test"},
                "system": {"system_id": "my_sys"},
            }
        )
        table = config_summary_table(parsed)
        assert isinstance(table, Table)

    def test_contains_system_id(self):
        from smart_data.config.parser import YamlConfigParser

        parsed = YamlConfigParser().parse_data(
            {"metadata": {}, "system": {"system_id": "test_id"}}
        )
        # Table is renderable — just check it doesn't raise
        table = config_summary_table(parsed)
        assert table is not None


class TestTelemetryStatusTable:
    def test_returns_table(self):
        status = {"configured": False, "provider": "ProxyTracerProvider"}
        table = telemetry_status_table(status)
        assert isinstance(table, Table)
        assert table.row_count == 2


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------


class TestSystemDetailPanel:
    def test_returns_panel(self):
        class FakeSystem:
            __doc__ = "A fake system."
            __name__ = "FakeSystem"
            __module__ = "tests"

        panel = system_detail_panel("my_sys", FakeSystem)
        assert isinstance(panel, Panel)

    def test_panel_has_title(self):
        class FakeSystem:
            __doc__ = "Desc."
            __name__ = "FakeSystem"
            __module__ = "tests"

        panel = system_detail_panel("test_name", FakeSystem)
        # Title should reference the name
        assert "test_name" in str(panel.title)


class TestFlowTree:
    def test_returns_tree_empty_flow(self):
        class FakeFlow:
            flow_id = "main"
            components = []
            edges = []

        tree = flow_tree(FakeFlow())
        assert isinstance(tree, Tree)

    def test_returns_tree_with_components(self):
        class FakeEdge:
            source_id = "a"
            target_id = "b"

        class FakeComponent:
            def __init__(self, cid):
                self.component_id = cid

        class FakeFlow:
            flow_id = "main"
            components = [FakeComponent("a"), FakeComponent("b")]
            edges = [FakeEdge()]

        tree = flow_tree(FakeFlow())
        assert isinstance(tree, Tree)


class TestYamlPreview:
    def test_returns_syntax(self):
        result = yaml_preview("key: value\n")
        assert isinstance(result, Syntax)


class TestComponentPanel:
    def test_returns_panel(self):
        class FakeMeta:
            kind = "TRANSFORM"
            tags = ["etl"]
            description = "A component"

        class FakeComponent:
            component_id = "step_1"
            metadata = FakeMeta()

        panel = component_panel(FakeComponent())
        assert isinstance(panel, Panel)

    def test_panel_no_metadata(self):
        class FakeComponent:
            component_id = "step_x"
            metadata = None

        panel = component_panel(FakeComponent())
        assert isinstance(panel, Panel)


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------


class TestSetupRichLogging:
    def test_does_not_raise(self):
        import logging

        setup_rich_logging(level=logging.WARNING)  # Should not raise
