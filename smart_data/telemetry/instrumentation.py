"""OpenTelemetry bootstrap helpers for smart-data."""

from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from opentelemetry.trace import Tracer


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
