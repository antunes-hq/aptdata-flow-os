"""Tests for telemetry secret masking helpers."""

from __future__ import annotations

from smart_data.telemetry.instrumentation import mask_telemetry_value, register_secret


class TestTelemetryMasking:
    def test_masks_registered_secret_substrings(self):
        register_secret("API_TOKEN", "top-secret")
        masked = mask_telemetry_value("Authorization: Bearer top-secret")
        assert masked == "Authorization: Bearer ****"

    def test_masks_sensitive_keys(self):
        masked = mask_telemetry_value({"Authorization": "Bearer abc", "ok": "1"})
        assert masked["Authorization"] == "****"
        assert masked["ok"] == "1"
