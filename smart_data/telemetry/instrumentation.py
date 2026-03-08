"""OpenTelemetry bootstrap helpers for smart-data."""

from __future__ import annotations

from collections.abc import Mapping

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.trace import Tracer

_SENSITIVE_KEYS = ("password", "secret", "token", "authorization", "api_key")
_REGISTERED_SECRETS: dict[str, str] = {}


def register_secret(name: str, value: str) -> None:
    """Register secret values so telemetry payloads can be masked."""
    _REGISTERED_SECRETS[name] = value


def get_registered_secret_names() -> list[str]:
    """Return registered secret keys, sorted for stable display."""
    return sorted(_REGISTERED_SECRETS)


def mask_telemetry_value(value: object, *, key: str | None = None) -> object:
    """Mask sensitive values before they are exported to telemetry/logs."""
    if value is None:
        return value
    if key is not None and any(token in key.lower() for token in _SENSITIVE_KEYS):
        return "****"
    if isinstance(value, str):
        masked = value
        for secret_value in _REGISTERED_SECRETS.values():
            if secret_value and secret_value in masked:
                masked = masked.replace(secret_value, "****")
        return masked
    if isinstance(value, Mapping):
        return {k: mask_telemetry_value(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [mask_telemetry_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_telemetry_value(item) for item in value)
    return value


def configure_telemetry(
    *,
    service_name: str = "smart-data",
    span_exporter: SpanExporter | None = None,
    metric_reader: MetricReader | None = None,
) -> tuple[TracerProvider, MeterProvider]:
    """Configure and register global tracer/meter providers."""
    resource = Resource.create({"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)
    if span_exporter is not None:
        tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    metric_readers = [metric_reader] if metric_reader is not None else []
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    return tracer_provider, meter_provider


def get_tracer(name: str = "smart_data.component") -> Tracer:
    """Return a configured tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str = "smart_data.component"):
    """Return a configured meter instance."""
    return metrics.get_meter(name)
