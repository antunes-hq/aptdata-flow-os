"""
Sistema de XP e Levels do mindflow.
XP por ação: nota (+5), qw_check (+3), chat (+10), briefing (+15), login (+5).
Levels com flora brasileira: Semente→Broto→Raiz→Caule→Galho→Bambu→Ipê→Jatobá→Baobá→Floresta.
"""
from __future__ import annotations

from datetime import datetime

XP_ACTIONS: dict[str, int] = {
    "nota": 5,
    "qw_check": 3,
    "chat": 10,
    "briefing": 15,
    "login": 5,
    "copa_view": 3,
}

LEVELS: list[dict] = [
    {"name": "Semente", "xp_required": 0, "emoji": "🌱"},
    {"name": "Broto", "xp_required": 50, "emoji": "🌿"},
    {"name": "Raiz", "xp_required": 150, "emoji": "🪵"},
    {"name": "Caule", "xp_required": 350, "emoji": "🌾"},
    {"name": "Galho", "xp_required": 700, "emoji": "🌳"},
    {"name": "Bambu", "xp_required": 1300, "emoji": "🎋"},
    {"name": "Ipê", "xp_required": 2200, "emoji": "🌸"},
    {"name": "Jatobá", "xp_required": 3500, "emoji": "🪨"},
    {"name": "Baobá", "xp_required": 5500, "emoji": "🌍"},
    {"name": "Floresta", "xp_required": 8000, "emoji": "🌴"},
]


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def add_xp(store, action: str, amount: int = None) -> dict:
    if amount is None:
        amount = XP_ACTIONS.get(action, 0)
    if amount <= 0:
        return {"xp": 0, "level": 0, "leveled_up": False, "new_level": None}

    total = get_xp_total(store) + amount
    store.set("mf_xp_total", total)

    old_level = get_level(store)

    log = store.get("mf_xp_log", [])
    log.append({"action": action, "xp": amount, "date": _today_str()})
    if len(log) > 200:
        log = log[-200:]
    store.set("mf_xp_log", log)

    new_level = get_level(store)
    leveled_up = new_level["level"] > old_level["level"]

    return {
        "xp": amount,
        "level": new_level["level"],
        "leveled_up": leveled_up,
        "new_level": new_level["name"] if leveled_up else None,
    }


def get_xp_total(store) -> int:
    return store.get("mf_xp_total", 0)


def get_level(store) -> dict:
    xp = get_xp_total(store)
    current_level = 0
    for i, lv in enumerate(LEVELS):
        if xp >= lv["xp_required"]:
            current_level = i
        else:
            break

    lv = LEVELS[current_level]
    if current_level < len(LEVELS) - 1:
        next_lv = LEVELS[current_level + 1]
        xp_in_level = xp - lv["xp_required"]
        xp_for_next = next_lv["xp_required"] - lv["xp_required"]
        next_xp = next_lv["xp_required"]
        progress_pct = min(100, round((xp_in_level / xp_for_next) * 100))
    else:
        next_xp = None
        progress_pct = 100

    return {
        "level": current_level,
        "name": lv["name"],
        "emoji": lv["emoji"],
        "current_xp": xp,
        "next_xp": next_xp,
        "progress_pct": progress_pct,
    }


def get_brisas(store) -> int:
    return store.get("mf_brisas", 0)
