"""Textual-based interactive monitoring dashboard.

Displays the pipeline DAG, memory usage and task status in real time.
"""

from __future__ import annotations

import os
import time
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Static


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
                            line.strip().split(":")
                            for line in f
                            if ":" in line
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


class MonitorApp(App):
    """Interactive monitoring dashboard for smart-data pipelines.

    Parameters
    ----------
    refresh_interval:
        How often (in seconds) the dashboard auto-refreshes.
    """

    TITLE = "smart-data monitor"
    SUB_TITLE = "Pipeline DAG & Task Status"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    CSS = """
    Screen {
        layout: vertical;
    }

    #top-row {
        height: 1fr;
        layout: horizontal;
    }

    #dag-panel {
        width: 1fr;
    }

    #status-panel {
        width: 2fr;
    }
    """

    def __init__(self, refresh_interval: float = 1.0, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._refresh_interval = refresh_interval
        self._status_table: _StatusTable | None = None
        self._memory_bar: _MemoryBar | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top-row"):
            yield _DAGPanel(id="dag-panel")
            with Vertical(id="status-panel"):
                yield _MemoryBar()
                yield _StatusTable()
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self._refresh_interval, self.action_refresh)

    def action_refresh(self) -> None:
        """Refresh all panels."""
        memory_bar = self.query_one(_MemoryBar)
        memory_bar.refresh_memory()

        table = self.query_one(_StatusTable)
        table.populate()
