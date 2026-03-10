"""Telemetry provider for injecting into context."""

from __future__ import annotations

from dataclasses import dataclass

from aptdata.telemetry.instrumentation import configure_telemetry, get_meter, get_tracer


@dataclass
class TelemetryProvider:
    """A wrapper providing telemetry resources."""

    _instance: TelemetryProvider | None = None

    @classmethod
    def get_instance(cls) -> TelemetryProvider:
        if cls._instance is None:
            # For scaffold default to configuring standard console telemetry
            configure_telemetry()
            cls._instance = cls()
        return cls._instance

    def get_tracer(self, name: str):
        return get_tracer(name)

    def get_meter(self, name: str):
        return get_meter(name)
