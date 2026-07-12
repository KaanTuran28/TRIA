"""Kapsama bosluğu analizi: risk yuksek ama devriyeye uzak bolgeleri tespit eder.

Yaklasim: son N gundeki onemli olaylarin her biri icin, O ANKI aktif (offline olmayan)
devriye birimlerine olan en yakin mesafeyi hesaplar. Sehir bazinda ortalama/maksimum
mesafe + olay yogunlugu birlestirilerek bir "kapsama boslugu skoru" uretilir — bu,
"nereye yeni devriye/karakol eklenmeli" sorusuna veri-temelli bir ilk yanit verir.

Not: Birimlerin GUNCEL konumu kullanilir (olay anindaki tarihsel konum degil) —
devriyeler surekli hareket ettigi icin bu bir yaklastirmadir, kesin tarihsel analiz
icin police_unit_history ile olay zamanina en yakin kayit eslestirilmelidir (bkz. CLAUDE.md yol haritasi).
"""

from __future__ import annotations

from typing import Any

from app.modules.c4i.dispatch import haversine_km

NO_COVERAGE_PENALTY_KM = 50.0  # aktif birim hic yoksa varsayilan "cok uzak" mesafe


def nearest_unit_distance(lat: float, lon: float, units: list[tuple[float, float]]) -> float:
    """(lat, lon) cift listesinden en yakin birime olan mesafe (km)."""
    if not units:
        return NO_COVERAGE_PENALTY_KM
    return min(haversine_km(lat, lon, u_lat, u_lon) for u_lat, u_lon in units)


def compute_coverage_report(
    incidents: list[dict[str, Any]],
    units: list[dict[str, Any]],
    top_n: int = 10,
) -> dict[str, Any]:
    """incidents: [{'city','lat','lon','severity_score'}, ...], units: [{'lat','lon'}, ...]."""
    unit_coords = [(u["lat"], u["lon"]) for u in units]

    by_city: dict[str, list[dict[str, Any]]] = {}
    for inc in incidents:
        if inc.get("lat") is None or inc.get("lon") is None:
            continue
        dist = nearest_unit_distance(inc["lat"], inc["lon"], unit_coords)
        city = (inc.get("city") or "bilinmeyen").lower()
        by_city.setdefault(city, []).append({**inc, "distance_km": dist})

    gaps = []
    for city, incs in by_city.items():
        distances = [i["distance_km"] for i in incs]
        severities = [float(i.get("severity_score") or 0) for i in incs]
        avg_distance = round(sum(distances) / len(distances), 2)
        max_distance = round(max(distances), 2)
        avg_severity = round(sum(severities) / len(severities), 2) if severities else 0.0
        # Skor: olay sayisi x ortalama siddet x ortalama mesafe — cok olay + uzak + siddetli = yuksek bosluk
        gap_score = round(len(incs) * avg_severity * avg_distance / 10.0, 1)
        gaps.append(
            {
                "city": city,
                "incident_count": len(incs),
                "avg_distance_km": avg_distance,
                "max_distance_km": max_distance,
                "avg_severity": avg_severity,
                "gap_score": gap_score,
            }
        )

    gaps.sort(key=lambda g: g["gap_score"], reverse=True)
    return {
        "unit_count": len(units),
        "incident_count": sum(len(v) for v in by_city.values()),
        "gaps": gaps[:top_n],
    }
