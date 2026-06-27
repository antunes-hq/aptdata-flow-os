"""aptdata.analytics — Context Intelligence Engine, memory stats, clusters, dedup."""
from aptdata.analytics.indicators import compute_espelho, compute_espelho_com_tendencia, _INDICATORS
from aptdata.analytics.stats import calc_memory_stats
from aptdata.analytics.clusters import cluster_notes
from aptdata.analytics.dedup import find_duplicates
