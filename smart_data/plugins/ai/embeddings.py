"""Embedding transformer plugin with token usage telemetry."""

from __future__ import annotations

import hashlib
from typing import Any

from opentelemetry import trace

from smart_data.plugins.dataset import InMemoryDataset
from smart_data.telemetry.instrumentation import record_llm_tokens_used


class EmbeddingTransformer:
    """Generate deterministic embeddings for text rows."""

    def __init__(
        self,
        *,
        column: str,
        model: str = "text-embedding-3-small",
    ) -> None:
        self.column = column
        self.model = model

    def transform(self, dataset: InMemoryDataset) -> InMemoryDataset:
        """Add embedding vectors and token usage metadata to each row."""
        rows = dataset.read()
        total_tokens = 0
        transformed: list[dict[str, Any]] = []
        with trace.get_tracer("smart_data.plugins.ai").start_as_current_span(
            "EmbeddingTransformer.transform"
        ) as span:
            for row in rows:
                text = str(row.get(self.column, ""))
                tokens = len(text.split())
                total_tokens += tokens
                enriched = dict(row)
                enriched["embedding_model"] = self.model
                enriched["embedding_tokens"] = tokens
                enriched[f"{self.column}_embedding"] = self._embed(text)
                transformed.append(enriched)
            span.set_attribute("llm.tokens.used", total_tokens)
            span.set_attribute("llm.model", self.model)
        record_llm_tokens_used(total_tokens)
        out = InMemoryDataset(uri=f"{dataset.uri}#embedded", schema_metadata=dict(dataset.schema_metadata))
        out.write(transformed)
        return out

    @staticmethod
    def _embed(text: str, *, dimensions: int = 8) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [int(digest[i]) / 255.0 for i in range(dimensions)]
