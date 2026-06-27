"""
mindflow.llm_observer — Observabilidade de chamadas LLM.

Captura tokens, latência e custo estimado de cada chamada ao DeepSeek.
Armazena como events kind='llm_call' no banco existente.
"""
from __future__ import annotations
import time
from typing import Any

# Preços DeepSeek (USD por 1M tokens, 2026-06)
# Modelo primário do app: deepseek-v4-flash ($0.15 / $0.25)
_PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.28, "output": 0.42},
    "deepseek-v4-flash": {"input": 0.30, "output": 0.50},
    "deepseek-v4-flash": {"input": 0.15, "output": 0.25},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}
_DEFAULT_PRICING = {"input": 0.15, "output": 0.25}


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = _PRICING.get(model, _DEFAULT_PRICING)
    return round((prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000, 8)


def log_llm_call(
    store,
    routine: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
) -> None:
    """Registra uma chamada LLM no banco. Silencioso em caso de erro."""
    try:
        cost = _estimate_cost(model, prompt_tokens, completion_tokens)
        store.log_event("mindflow", "llm_call", {
            "routine": routine,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "latency_ms": latency_ms,
            "cost_usd": cost,
            "version": "1",
        })
    except Exception:
        pass


def timed_create(client, routine: str, store, **kwargs) -> Any:
    """Wrapper em torno de client.chat.completions.create que loga automaticamente."""
    t0 = time.monotonic()
    resp = client.chat.completions.create(**kwargs)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if store is not None and hasattr(resp, "usage") and resp.usage:
        log_llm_call(
            store,
            routine=routine,
            model=kwargs.get("model", "deepseek-v4-flash"),
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            latency_ms=latency_ms,
        )
    return resp


def get_observability_summary(store, days: int = 7) -> dict:
    """Agrega stats de LLM calls dos últimos N dias."""
    import json
    from datetime import datetime, timezone, timedelta

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    try:
        conn = store._conn
        rows = conn.execute(
            "SELECT payload, created_at FROM events WHERE kind = 'llm_call' AND created_at >= ? ORDER BY created_at DESC",
            (cutoff,),
        ).fetchall()
    except Exception:
        rows = []

    total_calls = 0
    total_prompt = 0
    total_completion = 0
    total_cost = 0.0
    total_latency = 0
    by_routine: dict[str, dict] = {}
    recent: list[dict] = []

    for row in rows:
        try:
            p = json.loads(row[0]) if row[0] else {}
        except Exception:
            continue
        total_calls += 1
        pt = p.get("prompt_tokens", 0)
        ct = p.get("completion_tokens", 0)
        lat = p.get("latency_ms", 0)
        cost = p.get("cost_usd", 0.0)
        total_prompt += pt
        total_completion += ct
        total_latency += lat
        total_cost += cost

        rt = p.get("routine", "?")
        if rt not in by_routine:
            by_routine[rt] = {"calls": 0, "tokens": 0, "cost_usd": 0.0, "latency_ms_sum": 0}
        by_routine[rt]["calls"] += 1
        by_routine[rt]["tokens"] += pt + ct
        by_routine[rt]["cost_usd"] += cost
        by_routine[rt]["latency_ms_sum"] += lat

        if len(recent) < 20:
            recent.append({
                "routine": rt,
                "model": p.get("model", "?"),
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "latency_ms": lat,
                "cost_usd": cost,
                "ts": row[1],
            })

    routines_summary = []
    for rt, s in by_routine.items():
        routines_summary.append({
            "routine": rt,
            "calls": s["calls"],
            "tokens": s["tokens"],
            "cost_usd": round(s["cost_usd"], 6),
            "avg_latency_ms": round(s["latency_ms_sum"] / s["calls"]) if s["calls"] else 0,
        })
    routines_summary.sort(key=lambda x: x["calls"], reverse=True)

    return {
        "period_days": days,
        "total_calls": total_calls,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "total_cost_usd": round(total_cost, 6),
        "avg_latency_ms": round(total_latency / total_calls) if total_calls else 0,
        "by_routine": routines_summary,
        "recent": recent,
    }
