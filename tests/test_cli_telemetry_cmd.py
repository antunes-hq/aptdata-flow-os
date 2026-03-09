"""Tests for smart_data.cli.commands.telemetry_cmd."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from smart_data.cli.app import app
from smart_data.cli.commands.telemetry_cmd import _get_telemetry_status

runner = CliRunner()


# ---------------------------------------------------------------------------
# _get_telemetry_status helper
# ---------------------------------------------------------------------------


class TestGetTelemetryStatus:
    def test_returns_dict(self):
        status = _get_telemetry_status()
        assert isinstance(status, dict)

    def test_has_expected_keys(self):
        status = _get_telemetry_status()
        assert "configured" in status
        assert "provider" in status
        assert "service" in status

    def test_configured_is_bool(self):
        status = _get_telemetry_status()
        assert isinstance(status["configured"], bool)


# ---------------------------------------------------------------------------
# telemetry status
# ---------------------------------------------------------------------------


class TestTelemetryStatus:
    def test_status_exits_0(self):
        result = runner.invoke(app, ["telemetry", "status"])
        assert result.exit_code == 0

    def test_status_json_mode(self):
        result = runner.invoke(app, ["telemetry", "status", "--json"])
        assert result.exit_code == 0
        lines = [line for line in result.output.strip().splitlines() if line.strip()]
        assert len(lines) >= 1
        payload = json.loads(lines[0])
        assert "configured" in payload
        assert "provider" in payload

    def test_status_rich_mode_shows_provider(self):
        result = runner.invoke(app, ["telemetry", "status"])
        assert result.exit_code == 0
        # Should show the provider type in the table
        assert "provider" in result.output.lower() or "Provider" in result.output


# ---------------------------------------------------------------------------
# telemetry export
# ---------------------------------------------------------------------------


class TestTelemetryExport:
    def test_export_json_exits_0(self):
        result = runner.invoke(app, ["telemetry", "export"])
        assert result.exit_code == 0

    def test_export_json_format(self):
        result = runner.invoke(app, ["telemetry", "export", "--format", "json"])
        assert result.exit_code == 0
        # Output should be JSON
        assert "{" in result.output

    def test_export_invalid_format_exits_1(self):
        result = runner.invoke(app, ["telemetry", "export", "--format", "csv"])
        assert result.exit_code == 1
