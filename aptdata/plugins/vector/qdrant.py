"""Qdrant vector writer plugin."""

from __future__ import annotations

from typing import Any

from opentelemetry import trace

from aptdata.core.dataset import BaseDataset
from aptdata.plugins.vector.base import VectorWriter


class QdrantWriter(VectorWriter):
    """Write embeddings to an in-memory Qdrant-like collection buffer."""

    def __init__(self, *, collection: str, vector_column: str = "artigo_chunk_embedding") -> None:
        self.collection = collection
        self.vector_column = vector_column
        self.points: list[dict[str, Any]] = []

    def write(self, dataset: BaseDataset, **kwargs: Any) -> None:
        rows: list[dict[str, Any]] = dataset.read()
        with trace.get_tracer("aptdata.plugins.vector").start_as_current_span(
            "QdrantWriter.write"
        ) as span:
            for index, row in enumerate(rows):
                vector = row.get(self.vector_column)
                if vector is None:
                    continue
                point = {
                    "id": row.get("document_id") or row.get("id") or f"{self.collection}-{index}",
                    "vector": vector,
                    "payload": row,
                }
                self.points.append(point)
            span.set_attribute("aptdata.vector.collection", self.collection)
            span.set_attribute("aptdata.vector.points", len(self.points))
