"""Memory Lab — analytics e métricas da segunda mente."""
from __future__ import annotations

import json
from datetime import datetime, timedelta


def calc_memory_stats(store, vstore) -> dict:
    now = datetime.now()

    try:
        rows = vstore._conn.execute(
            "SELECT id, text, meta, created_at FROM notes"
        ).fetchall()
    except Exception:
        return {"total_notes": 0, "freshness_pct": 0, "topic_count": 0,
                "stale_pct": 0, "growth_weekly": {}, "top_keywords": []}

    total = len(rows)
    if total == 0:
        return {"total_notes": 0, "freshness_pct": 0, "topic_count": 0,
                "stale_pct": 0, "growth_weekly": {}, "top_keywords": []}

    cutoff = (now - timedelta(days=30)).isoformat()
    fresh = sum(1 for r in rows if (r[3] or "") >= cutoff)

    stale = 0
    for r in rows:
        try:
            meta = json.loads(r[2] or "{}")
            if meta.get("stale_at"):
                stale += 1
        except (json.JSONDecodeError, TypeError):
            pass

    growth: dict[str, int] = {}
    for r in rows:
        if r[3]:
            week = r[3][:7]
            growth[week] = growth.get(week, 0) + 1

    texts = [r[1] for r in rows if r[1]]
    from aptdata.analytics.tfidf import tfidf_keywords
    keywords = tfidf_keywords(texts, top_n=20) if texts else []

    events_total = 0
    try:
        events_total = store._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    except Exception:
        pass

    kinds_raw = store._conn.execute(
        "SELECT kind, COUNT(*) as cnt FROM events GROUP BY kind ORDER BY cnt DESC"
    ).fetchall()
    kinds = [{"kind": r[0], "count": r[1]} for r in kinds_raw]

    return {
        "total_notes": total,
        "total_events": events_total,
        "freshness_pct": round(fresh / total * 100, 1),
        "stale_pct": round(stale / total * 100, 1),
        "growth_weekly": dict(sorted(growth.items())),
        "top_keywords": keywords,
        "kinds": kinds,
    }
