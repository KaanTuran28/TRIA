"""Mevsimsel / gecmise-dayali suc istatistikleri: aylik dagilim + yaz aylari karsilastirmasi.

METODOLOJI NOTU (predictive.py'deki gibi seffaf): Bu gercek "mevsimsellik" tespiti DEGILDIR —
gercek mevsimsel dongu icin birden fazla yilin verisi gerekir. Su anki veri seti kisa bir zaman
araligini (haftalar/aylar) kapsadigi icin sonuclar o donemin aylik dagilimini yansitir, coklu-yil
dogrulanmis bir trend degil. Veri hacmi (ozellikle birden fazla yaz sezonu) arttikca bu analiz
daha guvenilir hale gelir.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

SUMMER_MONTHS = frozenset({6, 7, 8})  # Haziran-Temmuz-Agustos
SEASONAL_RISE_THRESHOLD_PCT = 20.0  # analytics/trends'deki RISING_THRESHOLD_PCT ile tutarli
MIN_SAMPLE_FOR_RISER = 3  # kucuk ornekte yanlis "artis" sinyali vermemek icin taban


def _pct_change(baseline: float, value: float) -> float:
    """value'nin baseline'a gore yuzde farki (baseline taban alinir)."""
    if baseline > 0:
        return round((value - baseline) / baseline * 100.0, 1)
    return 100.0 if value > 0 else 0.0


def compute_monthly_breakdown(rows: list[Any]) -> dict[int, dict[str, Any]]:
    """rows: 'month' (1-12) + 'severity_score' alanlari olan nesneler -> ay bazinda olay sayisi/ort. siddet."""
    by_month: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        by_month[int(r.month)].append(float(r.severity_score or 0))
    return {
        m: {
            "count": len(vals),
            "avg_severity": round(sum(vals) / len(vals), 1) if vals else 0.0,
        }
        for m, vals in sorted(by_month.items())
    }


def compute_seasonal_risers(rows: list[Any], group_key: str = "category") -> list[dict[str, Any]]:
    """rows: 'month' + group_key (ör. 'category'/'city') alanlari olan nesneler.

    Her grup icin yaz aylari (Haz-Agu) ortalama aylik olay sayisi ile diger 9 ayin
    ortalamasini kiyaslar. change_pct >= esik VE toplam olay sayisi >= taban ise
    'is_summer_riser' True olur (kucuk orneklemde yanlis alarm vermemek icin).
    """
    per_group_months: dict[str, dict[int, int]] = defaultdict(dict)
    for r in rows:
        key = getattr(r, group_key, None)
        if not key:
            continue
        month = int(r.month)
        per_group_months[key][month] = per_group_months[key].get(month, 0) + 1

    results = []
    for key, month_counts in per_group_months.items():
        summer_vals = [month_counts.get(m, 0) for m in SUMMER_MONTHS]
        rest_vals = [month_counts.get(m, 0) for m in range(1, 13) if m not in SUMMER_MONTHS]
        summer_avg = sum(summer_vals) / len(summer_vals) if summer_vals else 0.0
        rest_avg = sum(rest_vals) / len(rest_vals) if rest_vals else 0.0
        change_pct = _pct_change(rest_avg, summer_avg)
        total = sum(month_counts.values())
        # rest_avg == 0 iken "artis" isaretlemek yaniltici olur — bu genelde gercek bir mevsimsel
        # yukselisi degil, veri setinin o kategori icin yalnizca yaz aylarini kapsamasini yansitir
        # (ör. kisa sureli OSINT taramasi). Gercek bir "artis" icin yaz-disi donemde de taban olmali.
        is_riser = (
            rest_avg > 0
            and change_pct >= SEASONAL_RISE_THRESHOLD_PCT
            and total >= MIN_SAMPLE_FOR_RISER
        )
        results.append(
            {
                "group": key,
                "summer_avg_per_month": round(summer_avg, 1),
                "rest_avg_per_month": round(rest_avg, 1),
                "change_pct": change_pct,
                "total_incidents": total,
                "is_summer_riser": is_riser,
            }
        )
    results.sort(key=lambda r: r["change_pct"], reverse=True)
    return results
