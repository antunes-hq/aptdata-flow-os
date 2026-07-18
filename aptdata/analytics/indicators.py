"""
mindflow.context.analytics — Context Intelligence Engine: 8 indicadores do Espelho.

Calcula indicadores semanais a partir dos dados já existentes (events, kv, XP,
streak, quick wins, pérolas, LLM calls). Puro dado, zero IA — a síntese
narrativa vem depois (radar.py).

Indicadores (escala 0-100):
  🪞 consistencia   — streak, quick wins, dias ativos
  🧠 reflexao       — notas, aprendizado, pérolas geradas
  🗺️ exploracao     — mundos criados, personagens usados, temas testados
  📈 crescimento    — XP ganho na semana, progresso de level
  🤝 conexao        — profundidade de chat, variedade de personas
  🌊 fluxo          — sessões longas, imersão, distribuição temporal
  ✨ criacao        — ideias, mundos, temas, personas custom
  🌿 cuidado        — gratidão, check-ins com Doutor, bem-estar

Arquitetura: read-only sobre ContextStore. Nenhum write — o Espelho só lê.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

# Fuso Brasília
_BR_TZ = timezone(timedelta(hours=-3))


def _now() -> datetime:
    return datetime.now(_BR_TZ)


def _iso_days_ago(days: int) -> str:
    """Retorna data ISO (só YYYY-MM-DD) de `days` atrás no fuso BR."""
    return (_now() - timedelta(days=days)).strftime("%Y-%m-%d")


# ── thresholds de normalização (o que equivale a score 100) ─────────────────
# Ajustáveis conforme a base de usuários crescer. Por enquanto, calibrados
# para um usuário ativo que usa o app ~30min/dia.
_THRESHOLDS: dict[str, float] = {
    "consistencia_dias": 7,  # 7 dias ativos na semana = 100
    "consistencia_qw": 21,  # ~3 quick wins/dia = 100
    "reflexao_notas": 14,  # ~2 notas/dia = 100
    "reflexao_perolas": 7,  # 1 pérola/dia = 100
    "exploracao_mundos": 3,  # 3 mundos novos na semana = 100
    "exploracao_personas": 5,  # 5 personas distintas usadas = 100
    "crescimento_xp": 350,  # ~50 XP/dia = 100
    "conexao_tokens": 15000,  # ~2000 tokens/dia = 100
    "conexao_conversas": 14,  # ~2 conversas/dia = 100
    "fluxo_sessoes": 10,  # 10 sessões profundas = 100
    "criacao_ideias": 5,  # 5 ideias/semana = 100
    "criacao_temas": 2,  # 2 temas/semana = 100
    "cuidado_gratidoes": 5,  # ~1 gratidão/dia útil = 100
    "cuidado_doutor": 3,  # 3 check-ins/semana = 100
}


def _normalize(value: float, threshold: float) -> float:
    """Normaliza um valor bruto pra escala 0-100 contra um threshold."""
    if threshold <= 0:
        return 0.0
    return min(100.0, round((value / threshold) * 100, 1))


def _trend(current: float, previous: float) -> str:
    """Compara dois períodos e retorna tendência: 'up', 'down', 'stable'."""
    if previous == 0:
        return "up" if current > 0 else "stable"
    delta_pct = (current - previous) / previous
    if delta_pct > 0.05:
        return "up"
    if delta_pct < -0.05:
        return "down"
    return "stable"


def _count_events_in_range(
    store, kinds: list[str], since_days: int, until_days: int = 0
) -> int:
    """Conta eventos dos kinds dados num intervalo de dias.

    since_days: quantos dias atrás começa (ex: 14 = 14 dias atrás)
    until_days: quantos dias atrás termina (ex: 7 = 7 dias atrás, exclusivo)
    """
    since = _iso_days_ago(since_days)
    until = _iso_days_ago(until_days) if until_days > 0 else _now().strftime("%Y-%m-%d")
    try:
        placeholders = ",".join("?" * len(kinds))
        rows = store._conn.execute(
            f"SELECT COUNT(*) FROM events WHERE kind IN ({placeholders}) "
            f"AND created_at >= ? AND created_at < ?",
            (*kinds, since, until),
        ).fetchone()
        return rows[0] if rows else 0
    except Exception:
        return 0


def _count_events_week(store, kinds: list[str], weeks_ago: int = 0) -> int:
    """Conta eventos dos kinds dados nos últimos 7*weeks_ago dias.

    weeks_ago=0: última semana (0-7 dias atrás)
    weeks_ago=1: semana anterior (7-14 dias atrás)
    """
    start = 7 * (weeks_ago + 1)
    end = 7 * weeks_ago
    return _count_events_in_range(store, kinds, since_days=start, until_days=end)


# ── consultas específicas por indicador ─────────────────────────────────────


def _query_chat_stats(store, weeks_ago: int = 0) -> dict:
    """Tokens e conversas por chat na janela semanal."""
    start = 7 * (weeks_ago + 1)
    end = 7 * weeks_ago
    since = _iso_days_ago(start)
    until = _iso_days_ago(end) if end > 0 else _now().strftime("%Y-%m-%d")
    try:
        rows = store._conn.execute(
            "SELECT payload FROM events WHERE kind = 'llm_call' "
            "AND created_at >= ? AND created_at < ?",
            (since, until),
        ).fetchall()
        total_tokens = 0
        conversation_ids: set[str] = set()
        persona_set: set[str] = set()
        for (p,) in rows:
            try:
                data = json.loads(p) if p else {}
            except Exception:
                continue
            total_tokens += data.get("total_tokens", 0)
            rt = data.get("routine", "")
            if rt:
                conversation_ids.add(rt)
                # Extrai persona do nome da rotina (ex: "chat_brisa" → "brisa")
                if "_" in rt:
                    persona_set.add(rt)
        return {
            "tokens": total_tokens,
            "conversas": len(conversation_ids),
            "personas_distintas": len(persona_set),
        }
    except Exception:
        return {"tokens": 0, "conversas": 0, "personas_distintas": 0}


def _query_fluxo(store, weeks_ago: int = 0) -> dict:
    """Analisa padrão de uso: sessões longas, gaps, distribuição horária."""
    start = 7 * (weeks_ago + 1)
    end = 7 * weeks_ago
    since = _iso_days_ago(start)
    until = _iso_days_ago(end) if end > 0 else _now().strftime("%Y-%m-%d")
    try:
        rows = store._conn.execute(
            "SELECT kind, created_at FROM events "
            "WHERE created_at >= ? AND created_at < ? "
            "ORDER BY created_at ASC",
            (since, until),
        ).fetchall()
        if not rows:
            return {"sessoes_longas": 0, "maior_gap_horas": 99, "horarios_distintos": 0}

        timestamps = []
        horarios: set[int] = set()
        for _, ts in rows:
            try:
                dt = datetime.fromisoformat(ts)
                timestamps.append(dt)
                horarios.add(dt.hour)
            except (ValueError, TypeError):
                continue

        if len(timestamps) < 2:
            return {
                "sessoes_longas": 0,
                "maior_gap_horas": 99,
                "horarios_distintos": len(horarios),
            }

        # Sessões longas: clusters de eventos com gap < 30min entre ações
        sessoes_longas = 0
        sessao_start = timestamps[0]
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if gap > 1800:  # 30 min sem ação = fim de sessão
                duracao = (timestamps[i - 1] - sessao_start).total_seconds()
                if duracao > 600:  # sessão > 10 min = longa
                    sessoes_longas += 1
                sessao_start = timestamps[i]
        # Última sessão
        duracao = (timestamps[-1] - sessao_start).total_seconds()
        if duracao > 600:
            sessoes_longas += 1

        # Maior gap entre ações (em horas)
        gaps = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600
            for i in range(1, len(timestamps))
        ]
        maior_gap = max(gaps) if gaps else 0

        return {
            "sessoes_longas": sessoes_longas,
            "maior_gap_horas": round(maior_gap, 1),
            "horarios_distintos": len(horarios),
        }
    except Exception:
        return {"sessoes_longas": 0, "maior_gap_horas": 99, "horarios_distintos": 0}


# ── cálculo dos 8 indicadores ───────────────────────────────────────────────


def compute_consistencia(store, weeks_ago: int = 0) -> dict:
    """🔥 Consistência: streak, quick wins concluídos, dias ativos."""
    streak_info = store.get("mf_streak", 0)
    dias_ativos = 0

    # Dias ativos na semana: conta datas distintas com qw_done
    try:
        for d in range(7 * weeks_ago, 7 * (weeks_ago + 1)):
            day = _iso_days_ago(d)
            done = store.get(f"qw_done:{day}", [])
            # Também conta se teve eventos naquele dia
            if done:
                dias_ativos += 1
                continue
            # Fallback: conta eventos no dia
            rows = store._conn.execute(
                "SELECT 1 FROM events WHERE created_at >= ? AND created_at < ? LIMIT 1",
                (day, _iso_days_ago(d - 1) if d > 0 else _now().strftime("%Y-%m-%d")),
            ).fetchone()
            if rows:
                dias_ativos += 1
    except Exception:
        pass

    qw_done = 0
    try:
        for d in range(7 * weeks_ago, 7 * (weeks_ago + 1)):
            day = _iso_days_ago(d)
            done = store.get(f"qw_done:{day}", [])
            qw_done += len(done)
    except Exception:
        pass

    score = round(
        _normalize(dias_ativos, _THRESHOLDS["consistencia_dias"]) * 0.50
        + _normalize(qw_done, _THRESHOLDS["consistencia_qw"]) * 0.35
        + _normalize(streak_info, 30) * 0.15,  # 30 dias de streak = referência
        1,
    )

    return {
        "score": score,
        "dias_ativos": dias_ativos,
        "qw_concluidos": qw_done,
        "streak_atual": streak_info,
        "contribuintes": [
            f"{dias_ativos}/7 dias ativo" if dias_ativos > 0 else None,
            f"{qw_done} quick wins" if qw_done > 0 else None,
            f"streak 🔥{streak_info}" if streak_info > 0 else None,
        ],
    }


def compute_reflexao(store, weeks_ago: int = 0) -> dict:
    """🪞 Reflexão: notas, aprendizado, pérolas, briefings."""
    notas = _count_events_week(store, ["nota", "aprendizado"], weeks_ago)
    perolas = _count_events_week(store, ["pearl"], weeks_ago)
    briefings = _count_events_week(store, ["briefing"], weeks_ago)

    score = round(
        _normalize(notas, _THRESHOLDS["reflexao_notas"]) * 0.55
        + _normalize(perolas, _THRESHOLDS["reflexao_perolas"]) * 0.30
        + _normalize(briefings, 7) * 0.15,
        1,
    )

    return {
        "score": score,
        "notas_capturadas": notas,
        "perolas_geradas": perolas,
        "briefings": briefings,
        "contribuintes": [
            f"{notas} notas/aprendizados" if notas > 0 else None,
            f"{perolas} pérolas" if perolas > 0 else None,
            f"{briefings} briefings" if briefings > 0 else None,
        ],
    }


def compute_exploracao(store, weeks_ago: int = 0) -> dict:
    """🗺️ Exploração: mundos criados, personagens usados, temas."""
    mundos_criados = _count_events_week(store, ["world_created"], weeks_ago)
    temas_criados = _count_events_week(store, ["theme_created"], weeks_ago)

    # Personagens distintos usados em chat na semana
    chat_stats = _query_chat_stats(store, weeks_ago)
    personas_usadas = chat_stats["personas_distintas"]

    score = round(
        _normalize(mundos_criados, _THRESHOLDS["exploracao_mundos"]) * 0.40
        + _normalize(personas_usadas, _THRESHOLDS["exploracao_personas"]) * 0.40
        + _normalize(temas_criados, 2) * 0.20,
        1,
    )

    return {
        "score": score,
        "mundos_criados": mundos_criados,
        "personas_distintas": personas_usadas,
        "temas_criados": temas_criados,
        "contribuintes": [
            f"{mundos_criados} mundos novos" if mundos_criados > 0 else None,
            f"{personas_usadas} personagens usados" if personas_usadas > 0 else None,
            f"{temas_criados} temas criados" if temas_criados > 0 else None,
        ],
    }


def compute_crescimento(store, weeks_ago: int = 0) -> dict:
    """📈 Crescimento: XP ganho, progresso de level, total acumulado."""
    from aptdata.gamification import get_level, get_xp_total

    total_xp = get_xp_total(store)
    level = get_level(store)

    # XP ganho na semana via log
    xp_log = store.get("mf_xp_log", [])
    start_date = _iso_days_ago(7 * (weeks_ago + 1))
    end_date = (
        _iso_days_ago(7 * weeks_ago) if weeks_ago > 0 else _now().strftime("%Y-%m-%d")
    )
    xp_semana = sum(
        e["xp"] for e in xp_log if start_date <= e.get("date", "") < end_date
    )

    score = round(
        _normalize(xp_semana, _THRESHOLDS["crescimento_xp"]) * 0.70
        + level["progress_pct"] * 0.30,
        1,
    )

    return {
        "score": score,
        "xp_semana": xp_semana,
        "xp_total": total_xp,
        "level_atual": level["name"],
        "level_emoji": level["emoji"],
        "progresso_level_pct": level["progress_pct"],
        "contribuintes": [
            f"+{xp_semana} XP na semana" if xp_semana > 0 else None,
            f"Level {level['name']} {level['emoji']} ({level['progress_pct']}%)",
        ],
    }


def compute_conexao(store, weeks_ago: int = 0) -> dict:
    """🤝 Conexão: profundidade de chat, variedade de personas, interações."""
    stats = _query_chat_stats(store, weeks_ago)

    score = round(
        _normalize(stats["tokens"], _THRESHOLDS["conexao_tokens"]) * 0.50
        + _normalize(stats["conversas"], _THRESHOLDS["conexao_conversas"]) * 0.30
        + _normalize(stats["personas_distintas"], _THRESHOLDS["exploracao_personas"])
        * 0.20,
        1,
    )

    return {
        "score": score,
        "tokens_chat": stats["tokens"],
        "conversas": stats["conversas"],
        "personas_distintas": stats["personas_distintas"],
        "contribuintes": [
            f"{stats['tokens']} tokens em conversas" if stats["tokens"] > 0 else None,
            f"{stats['conversas']} conversas" if stats["conversas"] > 0 else None,
            f"{stats['personas_distintas']} personagens diferentes"
            if stats["personas_distintas"] > 0
            else None,
        ],
    }


def compute_fluxo(store, weeks_ago: int = 0) -> dict:
    """🌊 Fluxo: sessões longas, imersão, distribuição temporal."""
    fluxo = _query_fluxo(store, weeks_ago)

    # Quanto menor o maior gap, melhor (inverte)
    # gap de 0h = 100, gap de 12h+ = 0
    gap_score = max(0, 100 - (fluxo["maior_gap_horas"] / 12) * 100)

    score = round(
        _normalize(fluxo["sessoes_longas"], _THRESHOLDS["fluxo_sessoes"]) * 0.50
        + gap_score * 0.25
        + _normalize(fluxo["horarios_distintos"], 8) * 0.25,
        1,
    )

    return {
        "score": score,
        "sessoes_longas": fluxo["sessoes_longas"],
        "maior_gap_horas": fluxo["maior_gap_horas"],
        "horarios_distintos": fluxo["horarios_distintos"],
        "contribuintes": [
            f"{fluxo['sessoes_longas']} sessões profundas (>10min)"
            if fluxo["sessoes_longas"] > 0
            else None,
            f"Maior pausa: {fluxo['maior_gap_horas']}h"
            if fluxo["maior_gap_horas"] > 0
            else None,
            f"{fluxo['horarios_distintos']} horários diferentes"
            if fluxo["horarios_distintos"] > 0
            else None,
        ],
    }


def compute_criacao(store, weeks_ago: int = 0) -> dict:
    """✨ Criação: ideias, mundos, temas, personas custom."""
    ideias = _count_events_week(store, ["ideia"], weeks_ago)
    mundos = _count_events_week(store, ["world_created"], weeks_ago)
    temas = _count_events_week(store, ["theme_created"], weeks_ago)

    # Personas custom criadas (via kv)
    custom_personas = 0
    try:
        cp = store.get("persona_custom", {}) or {}
        custom_personas = len(cp)
    except Exception:
        pass

    score = round(
        _normalize(ideias, _THRESHOLDS["criacao_ideias"]) * 0.50
        + _normalize(mundos, _THRESHOLDS["exploracao_mundos"]) * 0.25
        + _normalize(temas, _THRESHOLDS["criacao_temas"]) * 0.15
        + _normalize(custom_personas, 3) * 0.10,
        1,
    )

    return {
        "score": score,
        "ideias": ideias,
        "mundos_criados": mundos,
        "temas_criados": temas,
        "personas_custom": custom_personas,
        "contribuintes": [
            f"{ideias} ideias" if ideias > 0 else None,
            f"{mundos} mundos" if mundos > 0 else None,
            f"{temas} temas" if temas > 0 else None,
            f"{custom_personas} personagens custom" if custom_personas > 0 else None,
        ],
    }


def compute_cuidado(store, weeks_ago: int = 0) -> dict:
    """🌿 Cuidado: gratidão, check-ins com Doutor/Cuida, bem-estar."""
    gratidoes = _count_events_week(store, ["gratidao"], weeks_ago)

    # Interações com Doutor
    doutor = _count_events_week(store, ["doutor"], weeks_ago)

    # Quick wins de bem-estar (detecção por nome/emoji)
    qw_cuidado = 0
    try:
        defs = store.get("qw_defs", []) or []
        bem_estar_keywords = [
            "água",
            "agua",
            "meditar",
            "meditação",
            "meditacao",
            "alongamento",
            "respirar",
            "pausa",
            "caminhada",
            "dormir",
            "sono",
            "exercício",
            "exercicio",
        ]
        for w in defs:
            nome_lower = w.get("nome", "").lower()
            if any(kw in nome_lower for kw in bem_estar_keywords):
                # Conta checks desse qw na semana
                for d in range(7 * weeks_ago, 7 * (weeks_ago + 1)):
                    day = _iso_days_ago(d)
                    done = store.get(f"qw_done:{day}", [])
                    if w.get("id") in done:
                        qw_cuidado += 1
    except Exception:
        pass

    score = round(
        _normalize(gratidoes, _THRESHOLDS["cuidado_gratidoes"]) * 0.40
        + _normalize(doutor, _THRESHOLDS["cuidado_doutor"]) * 0.35
        + _normalize(qw_cuidado, 14) * 0.25,
        1,
    )

    return {
        "score": score,
        "gratidoes": gratidoes,
        "checkins_doutor": doutor,
        "habitos_bem_estar": qw_cuidado,
        "contribuintes": [
            f"{gratidoes} gratidões" if gratidoes > 0 else None,
            f"{doutor} check-ins com Doutor" if doutor > 0 else None,
            f"{qw_cuidado} hábitos de bem-estar" if qw_cuidado > 0 else None,
        ],
    }


# ── aggregator principal ────────────────────────────────────────────────────

_INDICATORS: dict[str, dict] = {
    "consistencia": {"emoji": "🔥", "nome": "Consistência", "fn": compute_consistencia},
    "reflexao": {"emoji": "🪞", "nome": "Reflexão", "fn": compute_reflexao},
    "exploracao": {"emoji": "🗺️", "nome": "Exploração", "fn": compute_exploracao},
    "crescimento": {"emoji": "📈", "nome": "Crescimento", "fn": compute_crescimento},
    "conexao": {"emoji": "🤝", "nome": "Conexão", "fn": compute_conexao},
    "fluxo": {"emoji": "🌊", "nome": "Fluxo", "fn": compute_fluxo},
    "criacao": {"emoji": "✨", "nome": "Criação", "fn": compute_criacao},
    "cuidado": {"emoji": "🌿", "nome": "Cuidado", "fn": compute_cuidado},
}


def compute_espelho(store, weeks_ago: int = 0) -> dict:
    """Calcula todos os 8 indicadores para uma janela semanal.

    Args:
        store: ContextStore com os dados do usuário.
        weeks_ago: 0 = semana atual, 1 = semana anterior (pra tendência).

    Returns:
        dict com score_geral e lista de indicadores, cada um com
        {id, emoji, nome, score, detalhes, contribuintes}.
    """
    indicadores = []
    scores = []

    for ind_id, meta in _INDICATORS.items():
        try:
            data = meta["fn"](store, weeks_ago)
            # Filtra None dos contribuintes
            data["contribuintes"] = [c for c in data["contribuintes"] if c]
            indicadores.append(
                {
                    "id": ind_id,
                    "emoji": meta["emoji"],
                    "nome": meta["nome"],
                    "score": data["score"],
                    "detalhes": {
                        k: v
                        for k, v in data.items()
                        if k not in ("score", "contribuintes")
                    },
                    "contribuintes": data["contribuintes"],
                }
            )
            scores.append(data["score"])
        except Exception:
            indicadores.append(
                {
                    "id": ind_id,
                    "emoji": meta["emoji"],
                    "nome": meta["nome"],
                    "score": 0,
                    "detalhes": {},
                    "contribuintes": [],
                }
            )
            scores.append(0)

    score_geral = round(sum(scores) / len(scores), 1) if scores else 0

    return {
        "score_geral": score_geral,
        "indicadores": indicadores,
    }


def compute_espelho_com_tendencia(store) -> dict:
    """Calcula o Espelho completo: semana atual + tendência vs semana anterior.

    Returns:
        dict com espelho atual, anterior, e tendência por indicador.
    """
    atual = compute_espelho(store, weeks_ago=0)
    anterior = compute_espelho(store, weeks_ago=1)

    # Injeta tendência em cada indicador do atual
    anterior_map = {ind["id"]: ind for ind in anterior["indicadores"]}
    for ind in atual["indicadores"]:
        prev = anterior_map.get(ind["id"], {})
        prev_score = prev.get("score", 0)
        ind["score_anterior"] = prev_score
        ind["tendencia"] = _trend(ind["score"], prev_score)

    return {
        "atual": atual,
        "anterior": anterior,
        "tendencia_geral": _trend(atual["score_geral"], anterior["score_geral"]),
        "periodo": {
            "atual": {"inicio": _iso_days_ago(7), "fim": _now().strftime("%Y-%m-%d")},
            "anterior": {"inicio": _iso_days_ago(14), "fim": _iso_days_ago(7)},
        },
    }
