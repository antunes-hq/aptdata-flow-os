"""Textual-based interactive monitoring dashboard.

Displays the pipeline DAG, memory usage, task status and agent trace in
real time via a tabbed interface.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
)

from aptdata.mcp.server import get_mcp_status
from aptdata.telemetry.instrumentation import (
    get_ingestion_metrics,
    get_registered_secret_names,
)


class _DAGPanel(Static):
    """Simple ASCII DAG visualisation panel."""

    DEFAULT_CSS = """
    _DAGPanel {
        border: solid $success;
        height: 1fr;
        padding: 1 2;
    }
    """

    def on_mount(self) -> None:
        self.update(_placeholder_dag())


def _placeholder_dag() -> str:
    """Return a placeholder ASCII DAG when no pipeline is loaded."""
    return (
        "[bold green]Pipeline DAG[/bold green]\n\n"
        "  [cyan]● step_1[/cyan]\n"
        "      │\n"
        "  [cyan]● step_2[/cyan]\n"
        "      │\n"
        "  [cyan]● step_3[/cyan]\n\n"
        "[dim]No pipeline loaded – showing placeholder.[/dim]"
    )


class _StatusTable(DataTable):
    """Table showing per-task status and memory usage."""

    DEFAULT_CSS = """
    _StatusTable {
        border: solid $primary;
        height: 1fr;
    }
    """

    def on_mount(self) -> None:
        self.add_columns("Step", "Status", "Memory (MB)", "Elapsed (s)")
        self.populate()

    def populate(self) -> None:
        self.clear()
        # Placeholder rows – real data would come from a running pipeline
        for step, status, mem, elapsed in [
            ("step_1", "✅ done", "128", "0.42"),
            ("step_2", "⏳ running", "256", "1.07"),
            ("step_3", "⌛ pending", "—", "—"),
        ]:
            self.add_row(step, status, mem, elapsed)


class _MemoryBar(Static):
    """Simple memory usage indicator."""

    DEFAULT_CSS = """
    _MemoryBar {
        height: 3;
        padding: 0 2;
        background: $surface;
    }
    """

    def on_mount(self) -> None:
        self.refresh_memory()

    def refresh_memory(self) -> None:
        try:
            import psutil  # optional dependency

            mem = psutil.virtual_memory()
            pct = mem.percent
            used_gb = mem.used / 1_073_741_824
            total_gb = mem.total / 1_073_741_824
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            self.update(
                f"[bold]Memory:[/bold] [{bar}] {pct:.1f}%  "
                f"({used_gb:.2f} / {total_gb:.2f} GB)"
            )
        except ImportError:
            # psutil not installed – show basic info from /proc/meminfo
            try:
                with open("/proc/meminfo") as f:
                    lines = {
                        k: int(v.split()[0])
                        for k, v in (
                            line.strip().split(":") for line in f if ":" in line
                        )
                    }
                total = lines.get("MemTotal", 0)
                avail = lines.get("MemAvailable", 0)
                used = total - avail
                pct = (used / total * 100) if total else 0
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                self.update(
                    f"[bold]Memory:[/bold] [{bar}] {pct:.1f}%  "
                    f"(install psutil for detailed metrics)"
                )
            except Exception:  # noqa: BLE001
                self.update("[bold]Memory:[/bold] unavailable")


class _IngestionMetricsPanel(Static):
    """Panel with live ingestion throughput/cost/progress metrics."""

    DEFAULT_CSS = """
    _IngestionMetricsPanel {
        border: solid $success;
        height: 7;
        padding: 1 2;
    }
    """

    def on_mount(self) -> None:
        self.refresh_metrics()

    def refresh_metrics(self) -> None:
        metrics = get_ingestion_metrics()
        progress = float(metrics["progress_ratio"])
        bar_width = 24
        filled = int(progress * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        self.update(
            "[bold green]Ingestion Metrics[/bold green]\n"
            f"Throughput: {float(metrics['throughput_docs_per_sec']):.2f} docs/s\n"
            f"Chunks: {metrics['chunks_processed']}"
            f" | Tokens: {metrics['tokens_used']}\n"
            f"Progress: [{bar}] {progress * 100:.1f}%"
        )


class _AgentTraceLog(RichLog):
    """Log ao vivo do traço de observabilidade (mesmo store do viz/CLI).

    Lê incrementalmente do event store via cursor (``Observer.since``) —
    paridade com o SSE do aptdata-viz sobre a MESMA fonte.
    """

    DEFAULT_CSS = """
    _AgentTraceLog {
        border: solid $warning;
        height: 1fr;
        padding: 1 2;
    }
    """

    _cursor: int = 0

    def on_mount(self) -> None:
        self.write("[bold yellow]Agent Trace[/bold yellow]")
        if self.refresh_trace() == 0:
            self.write("[dim]Sem eventos ainda — aguardando routing/dispatch…[/dim]")

    def refresh_trace(self) -> int:
        """Puxa eventos novos do event store; devolve quantos entraram.

        Best-effort: observabilidade indisponível não pode derrubar a TUI.
        """
        try:
            from aptdata.observability import Observer  # noqa: PLC0415

            self._cursor, events = Observer.get().since(self._cursor, limit=100)
        except Exception:  # noqa: BLE001 - TUI degrada com graça
            return 0
        import json  # noqa: PLC0415
        from datetime import datetime  # noqa: PLC0415

        for event in events:
            when = datetime.fromtimestamp(event["ts"]).strftime("%H:%M:%S")
            agent = f" [cyan]{event['agent_id']}[/cyan]" if event["agent_id"] else ""
            payload = json.dumps(event["payload"], ensure_ascii=False)[:120]
            self.write(
                f"[dim]{when}[/dim] [bold]{event['kind']}[/bold]{agent} {payload}"
            )
        return len(events)


class _MCPStatusPanel(Static):
    """Panel showing MCP server status and secret injection metadata."""

    DEFAULT_CSS = """
    _MCPStatusPanel {
        border: solid $accent;
        height: 1fr;
        padding: 1 2;
    }
    """

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        status = get_mcp_status()
        secret_names = get_registered_secret_names()
        if secret_names:
            formatted_secrets = "\n".join(f"- {name}: ****" for name in secret_names)
        else:
            formatted_secrets = "- (none)"
        self.update(
            "[bold]MCP Status[/bold]\n"
            f"- Active: {'yes' if status['active'] else 'no'}\n"
            f"- Requests: {status['request_count']}\n\n"
            "[bold]Injected Secrets[/bold]\n"
            f"{formatted_secrets}"
        )


class MonitorApp(App):
    """Interactive monitoring dashboard for aptdata pipelines.

    The dashboard is divided into four tabs:

    1. **DAG View** – ASCII topology of the current pipeline.
    2. **Metrics** – Resource usage table and memory bar.
    3. **Agent Trace** – Real-time log of agent and routing events.
    4. **MCP Status** – MCP server activity and injected secret names.

    Parameters
    ----------
    refresh_interval:
        How often (in seconds) the dashboard auto-refreshes.
    """

    TITLE = "aptdata monitor"
    SUB_TITLE = "Pipeline DAG & Task Status"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }
    """

    def __init__(self, refresh_interval: float = 1.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._refresh_interval = refresh_interval

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent("DAG View", "Metrics", "Agent Trace", "MCP Status"):
            with TabPane("DAG View", id="dag-tab"):
                yield _DAGPanel(id="dag-panel")
            with TabPane("Metrics", id="metrics-tab"):
                with Vertical():
                    yield _MemoryBar()
                    yield _IngestionMetricsPanel()
                    yield _StatusTable()
            with TabPane("Agent Trace", id="agent-trace-tab"):
                yield _AgentTraceLog(id="agent-trace-log")
            with TabPane("MCP Status", id="mcp-status-tab"):
                yield _MCPStatusPanel(id="mcp-status-panel")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self._refresh_interval, self.action_refresh)

    def action_refresh(self) -> None:
        """Refresh all panels."""
        memory_bar = self.query_one(_MemoryBar)
        memory_bar.refresh_memory()

        table = self.query_one(_StatusTable)
        table.populate()

        ingestion_panel = self.query_one(_IngestionMetricsPanel)
        ingestion_panel.refresh_metrics()

        mcp_panel = self.query_one(_MCPStatusPanel)
        mcp_panel.refresh_status()

        trace_log = self.query_one(_AgentTraceLog)
        trace_log.refresh_trace()

    def log_agent_event(self, message: str) -> None:
        """Append *message* to the Agent Trace log tab."""
        trace_log = self.query_one(_AgentTraceLog)
        trace_log.write(message)
