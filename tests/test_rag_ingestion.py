"""Tests for resilience, AI plugins, vector writing, and ingestion telemetry."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from aptdata.core.state import StateBackend
from aptdata.core.workflow import Workflow
from aptdata.plugins.ai import EmbeddingTransformer, TextChunker
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.vector import QdrantWriter
from aptdata.telemetry.instrumentation import get_ingestion_metrics, reset_ingestion_metrics


class TestWorkflowResilience:
    def test_workflow_retries_and_checkpoint_resume(self, tmp_path):
        attempts = {"count": 0}
        backend = StateBackend(base_dir=tmp_path)

        def extract():
            dataset = InMemoryDataset(uri="memory://source")
            dataset.write([{"id": "1", "artigo": "texto inicial"}])
            return dataset

        def flaky_transform(dataset):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary failure")
            return dataset

        def fail_after_checkpoint(dataset):
            raise RuntimeError("stop for resume")

        wf = Workflow("ingestion_test", enable_checkpointing=True, state_backend=backend)
        wf.add_step(extract)
        wf.add_step(flaky_transform, retries=1, backoff=0)
        wf.add_step(fail_after_checkpoint)

        try:
            wf.execute()
        except RuntimeError:
            pass

        checkpoint_files = list(tmp_path.glob("*.json"))
        assert checkpoint_files
        run_id = checkpoint_files[0].stem
        state = backend.load(run_id)
        assert state["next_step_index"] == 2

        wf_resume = Workflow("ingestion_test", enable_checkpointing=True, state_backend=backend)
        wf_resume.add_step(extract)
        wf_resume.add_step(flaky_transform, retries=1, backoff=0)
        wf_resume.add_step(lambda dataset: dataset)

        resumed = wf_resume.resume(run_id)
        first_row = resumed.read()[0]
        assert first_row["document_id"] == "1"
        assert first_row["trace_id"]


class TestAIPlugins:
    def test_chunker_preserves_document_lineage(self):
        dataset = InMemoryDataset(uri="memory://docs")
        dataset.write(
            [
                {
                    "document_id": "doc-1",
                    "trace_id": "trace-abc",
                    "artigo": "Parágrafo um.\n\nParágrafo dois.",
                }
            ]
        )
        chunker = TextChunker(column="artigo", max_tokens=2)
        out = chunker.transform(dataset)
        rows = out.read()
        assert len(rows) >= 2
        assert all(row["document_id"] == "doc-1" for row in rows)
        assert all(row["trace_id"] == "trace-abc" for row in rows)
        assert all("artigo_chunk" in row for row in rows)

    def test_embeddings_track_tokens_and_add_vectors(self):
        reset_ingestion_metrics()
        dataset = InMemoryDataset(uri="memory://chunks")
        dataset.write([{"artigo_chunk": "um dois tres"}])
        embedder = EmbeddingTransformer(column="artigo_chunk")
        out = embedder.transform(dataset)
        row = out.read()[0]
        assert row["embedding_model"] == "text-embedding-3-small"
        assert len(row["artigo_chunk_embedding"]) == 8
        metrics = get_ingestion_metrics()
        assert metrics["tokens_used"] == 3


class TestVectorWriter:
    def test_qdrant_writer_persists_vectors(self):
        dataset = InMemoryDataset(uri="memory://embeddings")
        dataset.write(
            [
                {
                    "document_id": "d1",
                    "artigo_chunk_embedding": [0.1, 0.2],
                    "text": "chunk",
                }
            ]
        )
        writer = QdrantWriter(collection="support")
        writer.write(dataset)
        assert len(writer.points) == 1
        assert writer.points[0]["id"] == "d1"


class TestSpansLinkage:
    def test_pipeline_steps_share_same_trace(self):
        exporter = InMemorySpanExporter()
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.add_span_processor(SimpleSpanProcessor(exporter))
        else:
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

        dataset = InMemoryDataset(uri="memory://docs")
        dataset.write([{"id": "1", "text": "A B C"}])
        chunker = TextChunker(column="text", max_tokens=2)
        embedder = EmbeddingTransformer(column="artigo_chunk")
        writer = QdrantWriter(collection="support")

        wf = Workflow("trace_workflow", enable_checkpointing=False)
        wf.add_step(lambda: dataset)
        wf.add_step(chunker.transform)
        wf.add_step(embedder.transform)
        wf.add_step(writer.write)
        wf.execute()

        finished = exporter.get_finished_spans()
        trace_ids = {span.context.trace_id for span in finished}
        assert len(trace_ids) == 1
