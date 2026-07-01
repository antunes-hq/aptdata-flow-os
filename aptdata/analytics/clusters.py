"""Memory Lab — clustering de tópicos por similaridade semântica."""
from __future__ import annotations


def cluster_notes(vstore, n_clusters: int = 5) -> list[dict]:
    try:
        rows = vstore._conn.execute(
            "SELECT id, text, meta, embedding FROM notes WHERE embedding IS NOT NULL"
        ).fetchall()
    except Exception:
        return []

    if len(rows) < 3:
        texts = [{"id": r[0], "text": (r[1] or "")[:120]} for r in rows]
        return [{"topic": "Geral", "keywords": [], "notes": texts, "count": len(texts)}]

    texts = [r[1] for r in rows if r[1]]
    from aptdata.analytics.tfidf import tfidf_keywords
    all_keywords = tfidf_keywords(texts, top_n=30)

    clusters = []
    if len(all_keywords) <= n_clusters:
        kw_per_cluster = max(1, len(all_keywords))
        for i in range(0, len(all_keywords), kw_per_cluster):
            chunk = all_keywords[i:i + kw_per_cluster]
            related = []
            for r in rows:
                t = (r[1] or "").lower()
                if any(kw.lower() in t for kw in chunk):
                    related.append({"id": r[0], "text": (r[1] or "")[:120]})
            if related:
                clusters.append({
                    "topic": chunk[0].title() if chunk else "Geral",
                    "keywords": chunk,
                    "notes": related[:15],
                    "count": len(related),
                })

    if not clusters:
        clusters = [{
            "topic": "Geral",
            "keywords": all_keywords[:5],
            "notes": [
                {"id": r[0], "text": (r[1] or "")[:120]} for r in rows[:15]
            ],
            "count": len(rows),
        }]

    return clusters[:n_clusters]
