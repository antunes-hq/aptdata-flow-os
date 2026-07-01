"""Quick Wins — hábitos recorrentes com check.
Suporte a frequência: diária, semanal, dias específicos.

Lógica compartilhada entre a API (api/server.py) e a rotina "papo" (que cria/marca
quick wins por conversa). Defs vivem no kv `qw_defs`; o estado do dia em
`qw_done:<data>`; cada check também vira evento `kind="quickwin"` (pro histórico).
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

_DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
_DIA_ABRV = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex", 5: "sab", 6: "dom"}


def _hoje_eh_dia(dias: list[str] | None) -> bool:
    if not dias:
        return True
    hoje = _DIA_ABRV[date.today().weekday()]
    return hoje in dias


def get_defs(store) -> list[dict]:
    return store.get("qw_defs", []) or []


def _done(store, day: str) -> list[str]:
    return store.get(f"qw_done:{day}", []) or []


def streak(store, def_id: str) -> int:
    d = date.today()
    if def_id not in _done(store, d.isoformat()):
        d = d - timedelta(days=1)
    n = 0
    while def_id in _done(store, d.isoformat()):
        n += 1
        d = d - timedelta(days=1)
    return n


def list_status(store) -> dict:
    today = date.today().isoformat()
    done = _done(store, today)
    all_defs = get_defs(store)
    active = [w for w in all_defs if _hoje_eh_dia(w.get("dias"))]
    inactive = [
        {**w, "done_today": False, "streak": 0, "_inactive": True}
        for w in all_defs
        if not _hoje_eh_dia(w.get("dias"))
    ]
    items = [
        {**w, "done_today": w["id"] in done, "streak": streak(store, w["id"])}
        for w in active
    ]
    all_items = items + inactive
    return {
        "items": items,
        "done_count": sum(1 for i in items if i["done_today"]),
        "total": len(items),
        "total_defs": len(all_defs),
        "all_items": all_items,
    }


def create(
    store,
    nome: str,
    emoji: str = "✅",
    horarios: list | None = None,
    frequencia: str = "diaria",
    dias: list | None = None,
) -> dict | None:
    nome = (nome or "").strip()
    if not nome:
        return None
    defs = get_defs(store)
    w = {
        "id": uuid.uuid4().hex[:8],
        "nome": nome[:80],
        "emoji": (emoji or "✅")[:8],
        "horarios": horarios or [],
        "frequencia": frequencia,
        "dias": dias or [],
    }
    defs.append(w)
    store.set("qw_defs", defs)
    return w


def set_done(store, wid: str, want: bool, log_store=None) -> dict | None:
    today = date.today().isoformat()
    done = _done(store, today)
    defs = {w["id"]: w for w in get_defs(store)}
    if wid not in defs:
        return None
    if want and wid not in done:
        done.append(wid)
        store.set(f"qw_done:{today}", done)
        w = defs[wid]
        (log_store or store).log_event("web", "quickwin", {
            "text": f"{w['emoji']} {w['nome']}", "def_id": wid, "nome": w["nome"],
            "emoji": w["emoji"], "date": today, "type": "quickwin",
            "importance": 1, "version": "1",
        })
    elif not want and wid in done:
        done.remove(wid)
        store.set(f"qw_done:{today}", done)
    return {"done": want, "streak": streak(store, wid)}


def update(
    store, wid: str, nome=None, emoji=None, horarios=None,
    frequencia=None, dias=None,
) -> dict | None:
    defs = get_defs(store)
    w = next((x for x in defs if x["id"] == wid), None)
    if not w:
        return None
    if nome is not None:
        nome = nome.strip()
        if nome:
            w["nome"] = nome[:80]
    if emoji is not None and emoji.strip():
        w["emoji"] = emoji.strip()[:8]
    if horarios is not None:
        w["horarios"] = horarios
    if frequencia is not None:
        w["frequencia"] = frequencia
    if dias is not None:
        w["dias"] = dias
    store.set("qw_defs", defs)
    return w


def reorder(store, ids: list) -> None:
    defs = get_defs(store)
    by_id = {w["id"]: w for w in defs}
    nova = [by_id[i] for i in ids if i in by_id]
    nova += [w for w in defs if w["id"] not in set(ids)]
    store.set("qw_defs", nova)


def delete(store, wid: str) -> None:
    store.set("qw_defs", [w for w in get_defs(store) if w["id"] != wid])
