"""Tests for the TUI monitor (aptdata.tui.monitor).

These tests run the Textual MonitorApp in headless mode.
"""

from __future__ import annotations

import pytest

from aptdata.tui.monitor import (
    MonitorApp,
    _AgentTraceLog,
    _DAGPanel,
    _IngestionMetricsPanel,
    _MCPStatusPanel,
    _MemoryBar,
    _StatusTable,
)


@pytest.fixture()
def monitor_app() -> MonitorApp:
    return MonitorApp(refresh_interval=1.0)


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestMonitorAppInstantiation:
    def test_can_instantiate(self, monitor_app: MonitorApp) -> None:
        assert monitor_app is not None
        assert monitor_app.TITLE == "aptdata monitor"

    def test_custom_refresh_interval(self) -> None:
        app = MonitorApp(refresh_interval=0.5)
        assert app._refresh_interval == 0.5


# ---------------------------------------------------------------------------
# Headless rendering
# ---------------------------------------------------------------------------


class TestMonitorAppHeadless:
    @pytest.mark.asyncio()
    async def test_app_runs_headless(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            assert monitor_app.title == "aptdata monitor"

    @pytest.mark.asyncio()
    async def test_tabbed_content_present(self, monitor_app: MonitorApp) -> None:
        from textual.widgets import TabbedContent

        async with monitor_app.run_test():
            tc = monitor_app.query_one(TabbedContent)
            assert tc is not None

    @pytest.mark.asyncio()
    async def test_dag_panel_present(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            dag = monitor_app.query_one(_DAGPanel)
            assert dag is not None

    @pytest.mark.asyncio()
    async def test_status_table_present(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            table = monitor_app.query_one(_StatusTable)
            assert table is not None

    @pytest.mark.asyncio()
    async def test_memory_bar_present(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            mem = monitor_app.query_one(_MemoryBar)
            assert mem is not None

    @pytest.mark.asyncio()
    async def test_ingestion_metrics_panel_present(
        self, monitor_app: MonitorApp
    ) -> None:
        async with monitor_app.run_test():
            panel = monitor_app.query_one(_IngestionMetricsPanel)
            assert panel is not None
            assert "Ingestion Metrics" in str(panel.render())

    @pytest.mark.asyncio()
    async def test_agent_trace_present(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            trace = monitor_app.query_one(_AgentTraceLog)
            assert trace is not None

    @pytest.mark.asyncio()
    async def test_mcp_status_panel_present(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            panel = monitor_app.query_one(_MCPStatusPanel)
            assert panel is not None
            assert "MCP Status" in str(panel.render())

    @pytest.mark.asyncio()
    async def test_log_agent_event(self, monitor_app: MonitorApp) -> None:
        async with monitor_app.run_test():
            monitor_app.log_agent_event("test_event: branch_on triggered")
            trace = monitor_app.query_one(_AgentTraceLog)
            assert trace is not None


class TestAgentTraceEventStore:
    """O Agent Trace lê o MESMO event store da observability (fonte única)."""

    @pytest.mark.asyncio()
    async def test_backlog_loaded_on_mount(self, monitor_app: MonitorApp) -> None:
        from aptdata.observability import Observer

        Observer.get().emit("routing.decision", {"mode": "skill"}, agent_id="zeca")
        async with monitor_app.run_test():
            trace = monitor_app.query_one(_AgentTraceLog)
            assert trace._cursor >= 1  # backlog consumido no mount

    @pytest.mark.asyncio()
    async def test_refresh_appends_only_new_events(
        self, monitor_app: MonitorApp
    ) -> None:
        from aptdata.observability import Observer

        async with monitor_app.run_test():
            trace = monitor_app.query_one(_AgentTraceLog)
            assert trace.refresh_trace() == 0
            Observer.get().emit("agent.response", {"ok": True}, agent_id="zeca")
            assert trace.refresh_trace() == 1
            assert trace.refresh_trace() == 0  # cursor avançou

    @pytest.mark.asyncio()
    async def test_refresh_survives_broken_observer(
        self, monitor_app: MonitorApp, monkeypatch
    ) -> None:
        from aptdata import observability

        def _boom(cls):
            raise RuntimeError("store down")

        async with monitor_app.run_test():
            trace = monitor_app.query_one(_AgentTraceLog)
            monkeypatch.setattr(observability.Observer, "get", classmethod(_boom))
            assert trace.refresh_trace() == 0  # TUI não pode quebrar
