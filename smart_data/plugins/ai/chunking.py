"""Text chunking plugin for RAG ingestion pipelines."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from smart_data.plugins.dataset import InMemoryDataset
from smart_data.telemetry.instrumentation import record_processed_chunks


class TextChunker:
    """Split long text documents into chunked rows preserving lineage fields."""

    def __init__(
        self,
        *,
        column: str,
        max_tokens: int = 512,
        output_column: str | None = None,
    ) -> None:
        self.column = column
        self.max_tokens = max_tokens
        self.output_column = output_column or f"{column}_chunk"

    def transform(self, dataset: InMemoryDataset) -> InMemoryDataset:
        """Chunk each row's text and return a new dataset."""
        rows = dataset.read()
        chunked_rows: list[dict[str, Any]] = []
        with trace.get_tracer("smart_data.plugins.ai").start_as_current_span(
            "TextChunker.transform"
        ) as span:
            for row in rows:
                text = str(row.get(self.column, ""))
                paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
                doc_id = row.get("document_id") or row.get("id")
                trace_id = row.get("trace_id")
                chunk_index = 0
                for paragraph in paragraphs or [""]:
                    words = paragraph.split()
                    start = 0
                    while start < len(words) or (not words and start == 0):
                        chunk_words = words[start : start + self.max_tokens]
                        chunk_text = " ".join(chunk_words)
                        enriched = dict(row)
                        enriched[self.output_column] = chunk_text
                        enriched["chunk_index"] = chunk_index
                        if doc_id is not None:
                            enriched["document_id"] = doc_id
                        if trace_id is not None:
                            enriched["trace_id"] = trace_id
                        chunked_rows.append(enriched)
                        chunk_index += 1
                        if not words:
                            break
                        start += self.max_tokens
            record_processed_chunks(len(chunked_rows))
            span.set_attribute("smart_data.chunks.generated", len(chunked_rows))
        out = InMemoryDataset(uri=f"{dataset.uri}#chunked", schema_metadata=dict(dataset.schema_metadata))
        out.write(chunked_rows)
        return out
