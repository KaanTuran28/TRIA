"""Sehirler arasi karsilastirmali "guvenlik puan karti" — kurumsal sunum icin.

Performans (mudahale suresi), kapsama boslugu ve kisa donem suc trendini tek tabloda
birlestirir. `risk_index` BILIMSEL KESIN BIR SKOR DEGILDIR — sehirleri hizli
karsilastirmak icin ham degerlerin agirlikli toplamidir (predictive.py'deki erken uyari
skoru gibi seffaf/kural-tabanli, ML degil).
"""

from __future__ import annotations

from typing import Any

from app.modules.crime.population import POPULATION_2025

RESPONSE_WEIGHT = 0.4
GAP_WEIGHT = 0.4
TREND_WEIGHT = 0.2


def build_scorecard(
    performance_by_city: list[dict[str, Any]],
    coverage_gaps: list[dict[str, Any]],
    trend_zones: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Uc ayri analitik kaynagini sehir bazinda birlestirip risk_index'e gore siralar.

    Taban sehir kumesi TUIK 2025 il listesidir (POPULATION_2025) — yalnizca veri
    ureten sehirleri degil, tum 81 ili gosterir (`has_data=False` olanlar veri
    biriktikce dolacak "henuz olay/devriye kaydi yok" satirlaridir).
    """
    perf_map = {p["city"]: p for p in performance_by_city}
    gap_map = {g["city"]: g for g in coverage_gaps}
    trend_map = {t["city"]: t for t in trend_zones}
    cities = set(POPULATION_2025) | set(perf_map) | set(gap_map) | set(trend_map)

    rows = []
    for city in cities:
        perf = perf_map.get(city)
        gap = gap_map.get(city)
        trend = trend_map.get(city)
        has_data = bool(perf or gap or trend)

        avg_response = perf.get("avg") if perf else None
        gap_score = gap.get("gap_score", 0.0) if gap else 0.0
        change_pct = trend.get("change_pct", 0.0) if trend else 0.0
        recent_incidents = trend.get("current_period", 0) if trend else 0

        risk_index = round(
            (avg_response or 0.0) * RESPONSE_WEIGHT
            + gap_score * GAP_WEIGHT
            + max(change_pct, 0.0) * TREND_WEIGHT,
            1,
        )
        rows.append(
            {
                "city": city,
                "has_data": has_data,
                "avg_response_min": avg_response,
                "response_sample_size": perf.get("count", 0) if perf else 0,
                "gap_score": round(gap_score, 1),
                "trend_change_pct": change_pct,
                "recent_incidents": recent_incidents,
                "risk_index": risk_index,
            }
        )

    rows.sort(key=lambda r: (not r["has_data"], -r["risk_index"]))
    return rows
