"""OpenTelemetry bootstrap helpers for aptdata."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import perf_counter
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
_METRICS_LOCK = Lock()
_TOKEN_COUNTER = None


@dataclass
class IngestionMetrics:
    """Runtime ingestion metrics exposed to telemetry and the TUI monitor."""

    documents_total: int = 0
    documents_processed: int = 0
    chunks_processed: int = 0
    tokens_used: int = 0
    started_at: float = 0.0


_INGESTION_METRICS = IngestionMetrics()


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
        if not _REGISTERED_SECRETS:
            return value
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
    service_name: str = "aptdata",
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


def get_tracer(name: str = "aptdata.component") -> Tracer:
    """Return a configured tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str = "aptdata.component"):
    """Return a configured meter instance."""
    return metrics.get_meter(name)


def reset_ingestion_metrics() -> None:
    """Reset in-memory ingestion metrics for a new workflow run."""
    with _METRICS_LOCK:
        _INGESTION_METRICS.documents_total = 0
        _INGESTION_METRICS.documents_processed = 0
        _INGESTION_METRICS.chunks_processed = 0
        _INGESTION_METRICS.tokens_used = 0
        _INGESTION_METRICS.started_at = perf_counter()


def set_ingestion_total_documents(total: int) -> None:
    """Set total expected document count for progress tracking."""
    with _METRICS_LOCK:
        _INGESTION_METRICS.documents_total = max(total, 0)


def record_processed_documents(count: int) -> None:
    """Increment processed document count."""
    with _METRICS_LOCK:
        _INGESTION_METRICS.documents_processed += max(count, 0)


def record_processed_chunks(count: int) -> None:
    """Increment processed chunk count."""
    with _METRICS_LOCK:
        _INGESTION_METRICS.chunks_processed += max(count, 0)


def record_llm_tokens_used(tokens: int) -> None:
    """Track consumed LLM tokens in memory and OpenTelemetry metrics."""
    global _TOKEN_COUNTER
    if tokens <= 0:
        return
    with _METRICS_LOCK:
        _INGESTION_METRICS.tokens_used += tokens
    if _TOKEN_COUNTER is None:
        _TOKEN_COUNTER = get_meter("aptdata.ingestion").create_counter(
            "llm.tokens.used",
            description="Total LLM tokens consumed by embedding/LLM plugins.",
            unit="1",
        )
    _TOKEN_COUNTER.add(tokens)


def get_ingestion_metrics() -> dict[str, float | int]:
    """Return a snapshot of ingestion metrics with throughput and progress."""
    with _METRICS_LOCK:
        elapsed = max(perf_counter() - _INGESTION_METRICS.started_at, 0.0)
        docs = _INGESTION_METRICS.documents_processed
        total = _INGESTION_METRICS.documents_total
        progress = 1.0 if (total == 0 and docs > 0) else ((docs / total) if total else 0.0)
        throughput = (docs / elapsed) if elapsed > 0 else 0.0
        return {
            "documents_total": total,
            "documents_processed": docs,
            "chunks_processed": _INGESTION_METRICS.chunks_processed,
            "tokens_used": _INGESTION_METRICS.tokens_used,
            "throughput_docs_per_sec": throughput,
            "progress_ratio": min(progress, 1.0),
        }


reset_ingestion_metrics()
