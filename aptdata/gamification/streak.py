"""
Streak global do mindflow — dias consecutivos com pelo menos 1 ação.
Freeze: ganha 1 a cada 7 dias de streak, máx 2. Consome automaticamente se perder 1 dia.
"""
from __future__ import annotations

from datetime import datetime, timedelta


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def update_streak(store) -> dict:
    today = _today_str()
    streak = store.get("mf_streak", 0)
    freezes = store.get("mf_streak_freezes", 0)
    last_active = store.get("mf_last_active_date", "")
    max_streak = store.get("mf_max_streak", 0)

    result = {
        "streak": streak,
        "freezes": freezes,
        "streak_broken": False,
        "used_freeze": False,
    }

    if last_active == today:
        return result

    if not last_active:
        streak = 1
        store.set("mf_streak", streak)
        store.set("mf_last_active_date", today)
        if streak > max_streak:
            max_streak = streak
            store.set("mf_max_streak", max_streak)
        if streak % 7 == 0:
            freezes = min(freezes + 1, 2)
            store.set("mf_streak_freezes", freezes)
        result["streak"] = streak
        result["freezes"] = freezes
        return result

    last_date = _parse_date(last_active)
    today_date = _parse_date(today)
    diff = (today_date - last_date).days

    if diff == 1:
        streak += 1
        if streak % 7 == 0:
            freezes = min(freezes + 1, 2)
    elif diff > 1:
        if freezes > 0:
            freezes -= 1
            streak += 1
            result["used_freeze"] = True
        else:
            streak = 1
            result["streak_broken"] = True

    if streak > max_streak:
        max_streak = streak

    store.set("mf_streak", streak)
    store.set("mf_streak_freezes", freezes)
    store.set("mf_last_active_date", today)
    store.set("mf_max_streak", max_streak)

    result["streak"] = streak
    result["freezes"] = freezes
    return result


def get_streak(store) -> dict:
    return {
        "streak": store.get("mf_streak", 0),
        "freezes": store.get("mf_streak_freezes", 0),
        "last_active_date": store.get("mf_last_active_date", ""),
        "max_streak": store.get("mf_max_streak", 0),
    }
