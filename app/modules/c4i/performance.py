"""Dispatch performans KPI'lari: sevk gecikmesi, seyahat suresi, sahne suresi, toplam mudahale suresi.

Bu metrikler C4I sisteminin asil vaadini olculebilir kilar: "devriye agi olmadan
once vs sonra ortalama mudahale suresi ne kadar" sorusuna sayisal cevap verir.
Ham veri crime_events uzerindeki 4 zaman damgasindan turetilir:
  timestamp (olay) -> dispatched_at (sevk) -> arrived_at (varis) -> resolved_at (kapanis)
"""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any


def _minutes(a: datetime | None, b: datetime | None) -> float | None:
    """b - a farkini dakika olarak dondurur; biri eksikse None."""
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 60.0, 2)


def compute_incident_durations(row: Any) -> dict[str, float | None]:
    """Tek bir olay icin asama sureleri (dakika). row: timestamp/dispatched_at/arrived_at/resolved_at alanlari olan nesne."""
    return {
        "dispatch_delay_min": _minutes(row.timestamp, row.dispatched_at),
        "travel_time_min": _minutes(row.dispatched_at, row.arrived_at),
        "onscene_duration_min": _minutes(row.arrived_at, row.resolved_at),
        "total_response_min": _minutes(row.timestamp, row.resolved_at),
    }


def _percentile(values: list[float], pct: float) -> float | None:
    """Basit lineer interpolasyonlu yuzdelik (numpy bagimliligi yok)."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    if f == c:
        return round(s[f], 2)
    return round(s[f] + (s[c] - s[f]) * (k - f), 2)


def summarize_durations(values: list[float]) -> dict[str, float | None]:
    """Bir sure listesi icin avg/median/p90/min/max — deger yoksa hepsi None."""
    clean = [v for v in values if v is not None and v >= 0]
    if not clean:
        return {"avg": None, "median": None, "p90": None, "min": None, "max": None, "count": 0}
    return {
        "avg": round(sum(clean) / len(clean), 2),
        "median": round(median(clean), 2),
        "p90": _percentile(clean, 0.9),
        "min": round(min(clean), 2),
        "max": round(max(clean), 2),
        "count": len(clean),
    }


def build_performance_report(rows: list[Any]) -> dict[str, Any]:
    """crime_events satirlarindan (timestamp/dispatched_at/arrived_at/resolved_at/city/assigned_unit_id)
    genel + sehir bazli + birim bazli KPI raporu uretir."""
    per_row = [compute_incident_durations(r) for r in rows]

    overall = {
        "dispatch_delay_min": summarize_durations([d["dispatch_delay_min"] for d in per_row]),
        "travel_time_min": summarize_durations([d["travel_time_min"] for d in per_row]),
        "onscene_duration_min": summarize_durations([d["onscene_duration_min"] for d in per_row]),
        "total_response_min": summarize_durations([d["total_response_min"] for d in per_row]),
    }

    by_city: dict[str, list[float]] = {}
    by_unit: dict[str, list[float]] = {}
    for row, d in zip(rows, per_row):
        if d["total_response_min"] is not None:
            city = (row.city or "bilinmeyen").lower()
            by_city.setdefault(city, []).append(d["total_response_min"])
            if row.assigned_unit_id:
                by_unit.setdefault(row.assigned_unit_id, []).append(d["total_response_min"])

    city_stats = [
        {"city": city, **summarize_durations(vals)}
        for city, vals in sorted(by_city.items(), key=lambda kv: -len(kv[1]))
    ]
    unit_stats = [
        {"unit_id": unit_id, **summarize_durations(vals)}
        for unit_id, vals in sorted(by_unit.items(), key=lambda kv: -len(kv[1]))
    ]

    return {
        "sample_size": len(rows),
        "resolved_count": overall["total_response_min"]["count"],
        "overall": overall,
        "by_city": city_stats,
        "by_unit": unit_stats,
    }
