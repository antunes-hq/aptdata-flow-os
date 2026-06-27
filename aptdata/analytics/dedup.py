"""Memory Lab — detecção de duplicatas por similaridade."""
from __future__ import annotations

import json
from typing import Any


def find_duplicates(vstore, threshold: float = 0.92) -> list[dict]:
    try:
        rows = vstore._conn.execute(
            "SELECT id, text, meta, created_at FROM notes WHERE text IS NOT NULL ORDER BY created_at DESC"
        ).fetchall()
    except Exception:
        return []

    if len(rows) < 2:
        return []

    from difflib import SequenceMatcher

    duplicates = []
    seen = set()

    for i in range(len(rows)):
        for j in range(i + 1, min(i + 30, len(rows))):
            if rows[i][0] in seen or rows[j][0] in seen:
                continue
            a = (rows[i][1] or "").lower().strip()
            b = (rows[j][1] or "").lower().strip()
            if len(a) < 20 or len(b) < 20:
                continue
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= threshold:
                seen.add(rows[i][0])
                seen.add(rows[j][0])
                duplicates.append({
                    "note_a": {"id": rows[i][0], "text": a[:200], "date": rows[i][3]},
                    "note_b": {"id": rows[j][0], "text": b[:200], "date": rows[j][3]},
                    "score": round(ratio, 3),
                })
            if len(duplicates) >= 10:
                break
        if len(duplicates) >= 10:
            break

    return duplicates
