"""SmartConsole — dual-mode (Rich / JSON) output for aptdata CLI."""

from __future__ import annotations

import json
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.status import Status
from rich.theme import Theme

_THEME = Theme(
    {
        "info": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "event": "dim white",
    }
)


class SmartConsole:
    """Dual-mode console: Rich for humans, JSON lines for machines.

    Parameters
    ----------
    json_mode:
        When *True*, all output is emitted as JSON lines (backward-compat).
        When *False* (default), Rich markup is used for human-friendly output.
    """

    def __init__(self, json_mode: bool = False) -> None:
        self.json_mode = json_mode
        self._console = Console(theme=_THEME, highlight=False)
        self._err_console = Console(theme=_THEME, stderr=True, highlight=False)

    # ------------------------------------------------------------------
    # Core output helpers
    # ------------------------------------------------------------------

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to stdout using Rich (or plain text in json_mode)."""
        if self.json_mode:
            print(*args, flush=True)
        else:
            self._console.print(*args, **kwargs)

    def emit_event(self, event: str, **data: Any) -> None:
        """Emit a structured event. In JSON mode: JSON line. In Rich mode: formatted."""
        payload = {"event": event, **data}
        if self.json_mode:
            print(json.dumps(payload, default=str), flush=True)
        else:
            self._console.print(
                f"[event]▶ {event}[/event]", json.dumps(data, default=str)
            )

    def info(self, msg: str) -> None:
        """Emit an informational message."""
        if self.json_mode:
            print(
                json.dumps({"level": "info", "message": msg}, default=str), flush=True
            )
        else:
            self._console.print(f"[info]ℹ {msg}[/info]")

    def success(self, msg: str) -> None:
        """Emit a success message."""
        if self.json_mode:
            print(
                json.dumps({"level": "success", "message": msg}, default=str),
                flush=True,
            )
        else:
            self._console.print(f"[success]✓ {msg}[/success]")

    def warning(self, msg: str) -> None:
        """Emit a warning message."""
        if self.json_mode:
            print(
                json.dumps({"level": "warning", "message": msg}, default=str),
                flush=True,
            )
        else:
            self._console.print(f"[warning]⚠ {msg}[/warning]")

    def error(self, msg: str) -> None:
        """Emit an error message to stderr."""
        if self.json_mode:
            print(
                json.dumps({"level": "error", "message": msg}, default=str),
                file=sys.stderr,
                flush=True,
            )
        else:
            self._err_console.print(f"[error]✗ {msg}[/error]")

    def rule(self, title: str = "") -> None:
        """Print a horizontal rule (no-op in json_mode)."""
        if not self.json_mode:
            self._console.rule(title)

    def render(self, renderable: Any) -> None:
        """Render a Rich renderable (table, panel, tree, …). No-op in json_mode."""
        if not self.json_mode:
            self._console.print(renderable)

    @contextmanager
    def spinner(self, msg: str) -> Generator[None, None, None]:
        """Context manager that shows a spinner in Rich mode (no-op in json_mode)."""
        if self.json_mode:
            yield
        else:
            with Status(msg, console=self._console):
                yield
