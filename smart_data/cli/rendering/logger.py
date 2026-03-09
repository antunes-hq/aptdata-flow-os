"""Rich logging setup for smart-data CLI."""

from __future__ import annotations

import logging


def setup_rich_logging(level: int = logging.INFO) -> None:
    """Configure the root logger to use RichHandler for human-friendly output.

    Parameters
    ----------
    level:
        Logging level (default: INFO).
    """
    try:
        from rich.logging import RichHandler  # noqa: PLC0415

        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        )
    except ImportError:
        logging.basicConfig(level=level)
