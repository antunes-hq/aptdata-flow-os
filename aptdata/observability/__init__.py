"""aptdata.observability — traço de eventos do ecossistema + custo de LLM.

- :class:`Observer` — façade best-effort (nunca levanta) com correlação por
  ``run_id``; veja ``observer.py`` para a taxonomia de eventos.
- :class:`ObservabilityStore` — event store SQLite próprio do aptdata.
- ``llm_observer`` — tracking de custo/latência de chamadas LLM (legado
  mindflow; migração para o store próprio planejada).
"""

from aptdata.observability.llm_observer import (
    _PRICING,
    get_observability_summary,
    log_llm_call,
    timed_create,
)
from aptdata.observability.observer import Observer
from aptdata.observability.store import ObservabilityStore

__all__ = [
    "_PRICING",
    "Observer",
    "ObservabilityStore",
    "get_observability_summary",
    "log_llm_call",
    "timed_create",
]
