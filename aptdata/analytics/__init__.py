"""aptdata.analytics — Context Intelligence Engine, memory stats, clusters, dedup."""

from aptdata.analytics.clusters import cluster_notes
from aptdata.analytics.dedup import find_duplicates
from aptdata.analytics.indicators import (
    _INDICATORS,
    compute_espelho,
    compute_espelho_com_tendencia,
)
from aptdata.analytics.stats import calc_memory_stats

__all__ = [
    "cluster_notes",
    "find_duplicates",
    "_INDICATORS",
    "compute_espelho",
    "compute_espelho_com_tendencia",
    "calc_memory_stats",
]
