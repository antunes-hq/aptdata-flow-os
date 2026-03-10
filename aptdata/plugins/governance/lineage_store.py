"""In-memory lineage graph store for persisting and querying workflow runs."""

from __future__ import annotations

from aptdata.core.lineage import LineageGraph


class LineageStore:
    """In-memory store for :class:`~aptdata.core.lineage.LineageGraph` objects.

    Each workflow run produces exactly one :class:`LineageGraph` which is
    saved under its :attr:`~LineageGraph.run_id`.

    Examples
    --------
    ::

        store = LineageStore()
        store.save(graph)
        loaded = store.load(run_id)
        runs = store.list_runs()
        graphs = store.query_by_dataset("s3://bucket/data.parquet")
    """

    def __init__(self) -> None:
        self._store: dict[str, LineageGraph] = {}

    def save(self, graph: LineageGraph) -> None:
        """Persist *graph* under its :attr:`~LineageGraph.run_id`."""
        self._store[graph.run_id] = graph

    def load(self, run_id: str) -> LineageGraph | None:
        """Return the graph for *run_id*, or ``None`` if not found."""
        return self._store.get(run_id)

    def list_runs(self) -> list[str]:
        """Return a sorted list of all stored run IDs."""
        return sorted(self._store)

    def query_by_dataset(self, uri: str) -> list[LineageGraph]:
        """Return all graphs that contain at least one node referencing *uri*."""
        return [
            graph
            for graph in self._store.values()
            if any(node.dataset_uri == uri for node in graph.nodes)
        ]


__all__ = ["LineageStore"]
