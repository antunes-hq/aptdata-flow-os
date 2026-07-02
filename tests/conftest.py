"""Shared fixtures and utilities for the aptdata test suite.

This conftest.py provides:
- Reusable pytest fixtures (DataFrame factories, InMemoryDataset, CLI runner)
- Helper utilities for JSON-line output parsing
- Module-level markers for test categorisation (unit / integration / e2e)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Pytest markers
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so -m filters work without warnings."""
    config.addinivalue_line("markers", "unit: fast, isolated unit tests")
    config.addinivalue_line(
        "markers", "integration: tests that wire multiple components together"
    )
    config.addinivalue_line("markers", "e2e: end-to-end CLI / workflow tests")


# ---------------------------------------------------------------------------
# Observability isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_observability(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Aponta o event store para um banco temporário em TODOS os testes.

    O Router/adapters emitem eventos por padrão; sem isolamento a suite
    escreveria em ``~/.aptdata/events.db`` (e testes vazariam uns nos outros).
    """
    monkeypatch.setenv("APTDATA_OBS_DB", str(tmp_path / "obs-events.db"))
    from aptdata.observability import Observer  # noqa: PLC0415

    Observer.reset()
    yield
    Observer.reset()


# ---------------------------------------------------------------------------
# DataFrame helpers (require pandas)
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_df():
    """Factory fixture that returns a helper to build small DataFrames.

    Usage::

        def test_something(make_df):
            df = make_df({"id": [1, 2], "value": [10, 20]})
            ...
    """
    pd = pytest.importorskip("pandas")

    def _make(**columns: list) -> Any:
        return pd.DataFrame(columns)

    return _make


@pytest.fixture()
def simple_df(make_df):
    """A small DataFrame with ``id``, ``name``, and ``value`` columns."""
    return make_df(id=[1, 2, 3], name=["alice", "bob", "carol"], value=[10, 20, 30])


# ---------------------------------------------------------------------------
# InMemoryDataset helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_dataset():
    """Factory fixture that creates
    :class:`~aptdata.plugins.dataset.InMemoryDataset` instances.

    Usage::

        def test_something(make_dataset):
            ds = make_dataset([{"id": 1}, {"id": 2}], uri="memory://test")
            ...
    """
    from aptdata.plugins.dataset import InMemoryDataset  # noqa: PLC0415

    def _make(
        records: list[dict], uri: str = "memory://test", schema: dict | None = None
    ) -> InMemoryDataset:
        ds = InMemoryDataset(uri=uri, schema_metadata=schema or {})
        ds.write(records)
        return ds

    return _make


@pytest.fixture()
def sample_dataset(make_dataset):
    """A small InMemoryDataset with three records."""
    return make_dataset(
        [{"id": 1, "val": 10}, {"id": 2, "val": 20}, {"id": 3, "val": 30}]
    )


# ---------------------------------------------------------------------------
# CLI runner helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def cli_runner():
    """A pre-configured :class:`typer.testing.CliRunner`."""
    from typer.testing import CliRunner  # noqa: PLC0415

    return CliRunner()


@pytest.fixture()
def cli_app():
    """The main aptdata Typer application."""
    from aptdata.cli.app import app  # noqa: PLC0415

    return app


def parse_json_lines(output: str) -> list[dict]:
    """Parse all valid JSON lines from CLI output.

    Parameters
    ----------
    output:
        Raw string output from a CLI invocation.

    Returns
    -------
    list[dict]
        Parsed JSON objects, one per non-empty line.
    """
    results = []
    for line in output.strip().splitlines():
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return results


def assert_json_event(output: str, event: str) -> dict:
    """Assert that *event* appears in the JSON-line output and return its payload.

    Parameters
    ----------
    output:
        Raw CLI output.
    event:
        Expected ``"event"`` field value.

    Returns
    -------
    dict
        The first matching event payload.

    Raises
    ------
    AssertionError
        When the event is not found.
    """
    payloads = parse_json_lines(output)
    matches = [p for p in payloads if p.get("event") == event]
    assert matches, (
        f"Event '{event}' not found in output."
        f" Got: {[p.get('event') for p in payloads]}"
    )
    return matches[0]


# ---------------------------------------------------------------------------
# Temporary project directory fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def scaffolded_project(tmp_path: Path, cli_runner, cli_app):
    """Scaffold a hello-world project and return its directory.

    Useful for integration/e2e tests that need a complete project structure.
    """
    result = cli_runner.invoke(
        cli_app,
        ["scaffold", "test_project", "--output", str(tmp_path)],
    )
    assert result.exit_code == 0, f"Scaffold failed: {result.output}"
    return tmp_path / "test_project"
