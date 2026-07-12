"""Prediktif risk skoru: kisa vadeli yogunluk sapmasi + orta vadeli trend + siddet.

ONEMLI (metodoloji notu): Bu egitilmis bir ML modeli DEGILDIR — yorumlanabilir,
kurala dayali bir erken-uyari skorudur. Il basina saatlik olay hacmi, gun-ici/haftalik
mevsimsellik icin (orn. saat-of-day x gun-of-week Poisson regresyonu) istatistiksel
olarak guvenilir bir egitim kumesi olusturacak kadar yuksek degil; bu yuzden kasitli
olarak basit ve seffaf bir formul tercih edildi. Veri hacmi buyudukce CLAUDE.md'deki
yol haritasinda belirtilen kalibre edilmis modele gecilmesi onerilir.

Formul: score = 100 * (0.45*yogunluk_sapmasi + 0.30*trend + 0.25*ortalama_siddet)
- yogunluk_sapmasi: son pencerenin saatlik hizi / tarihsel taban saatlik hiz (2x'te tavan)
- trend: son 7g vs onceki 7g yuzde artisi (+%50'de tavan, negatifler 0'a kirpilir)
- ortalama_siddet: son penceredeki ortalama siddet / 10
"""

from __future__ import annotations

RISK_LEVELS = (
    (75.0, "critical"),
    (55.0, "high"),
    (35.0, "medium"),
    (0.0, "low"),
)


def _risk_level(score: float) -> str:
    for threshold, label in RISK_LEVELS:
        if score >= threshold:
            return label
    return "low"


def compute_predictive_score(
    *,
    recent_count: int,
    recent_hours: float,
    baseline_count: int,
    baseline_hours: float,
    avg_severity_recent: float,
    trend_pct: float,
) -> dict:
    recent_rate = recent_count / max(recent_hours, 0.01)
    baseline_rate = baseline_count / max(baseline_hours, 0.01)
    # baseline_rate cok dusukse (yeni/az olaylı il) oran patlamasin diye taban epsilon
    intensity_ratio = recent_rate / max(baseline_rate, 0.02)

    intensity_component = min(intensity_ratio / 2.0, 1.0)
    trend_component = min(max(trend_pct, 0.0) / 50.0, 1.0)
    severity_component = min(max(avg_severity_recent, 0.0) / 10.0, 1.0)

    score = 100.0 * (0.45 * intensity_component + 0.30 * trend_component + 0.25 * severity_component)
    score = round(max(0.0, min(100.0, score)), 1)

    return {
        "predictive_score": score,
        "risk_level": _risk_level(score),
        "intensity_ratio": round(intensity_ratio, 2),
        "recent_rate_per_hour": round(recent_rate, 3),
        "baseline_rate_per_hour": round(baseline_rate, 3),
    }
