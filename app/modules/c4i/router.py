"""C4I API: canli devriye takibi, trend analitigi, kritik olay akisi."""

from __future__ import annotations

import asyncio
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.database import AsyncSessionLocal, get_db
from app.modules.c4i.coverage import compute_coverage_report
from app.modules.c4i.dispatch import priority_score
from app.modules.c4i.models import PoliceUnit, PoliceUnitHistory
from app.modules.c4i.performance import build_performance_report
from app.modules.c4i.predictive import compute_predictive_score
from app.modules.c4i.simulation import TICK_SECONDS, seed_police_units
from app.modules.crime.geometry_utils import utcnow_naive
from app.modules.crime.models import CrimeEvent
from app.modules.crime.population import per_100k
from app.modules.crime.services import CITY_COORDS

router = APIRouter(prefix="/api/v1", tags=["C4I"])

RISING_THRESHOLD_PCT = 20.0  # bu esigin ustu "yukselen risk bolgesi"

# Analitik sorgular agir group-by icerir; coklu istemci ayni sonucu 30 sn paylasir.
_CACHE_TTL_S = 30.0
_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(key: str) -> dict | None:
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL_S:
        return hit[1]
    return None


def _cache_put(key: str, value: dict) -> dict:
    _cache[key] = (time.monotonic(), value)
    return value


def pct_change(current: int, previous: int) -> float:
    """Iki donem arasi yuzdesel degisim; onceki donem 0 ise 0/100 kurali."""
    if previous > 0:
        return round((current - previous) / previous * 100.0, 1)
    return 100.0 if current > 0 else 0.0


# ---------------------------------------------------------------- birimler

async def _units_payload(db: AsyncSession) -> dict:
    """Devriye birimlerinin anlik GeoJSON'u — REST ve WebSocket ayni ciktiyi paylasir."""
    rows = (
        await db.execute(
            select(
                PoliceUnit.unit_id,
                PoliceUnit.unit_type,
                PoliceUnit.status,
                PoliceUnit.city,
                PoliceUnit.speed_kmh,
                PoliceUnit.last_update,
                PoliceUnit.assigned_route,
                func.ST_X(PoliceUnit.current_location).label("lon"),
                func.ST_Y(PoliceUnit.current_location).label("lat"),
            ).where(PoliceUnit.current_location.isnot(None))
        )
    ).all()

    features = []
    counts = {"patrolling": 0, "responding": 0, "offline": 0}
    for r in rows:
        counts[r.status] = counts.get(r.status, 0) + 1
        route = r.assigned_route or {}
        dispatch_mode = route.get("mode")
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(r.lon), float(r.lat)]},
                "properties": {
                    "unit_id": r.unit_id,
                    "unit_type": r.unit_type,
                    "status": r.status,
                    "city": r.city,
                    "speed_kmh": r.speed_kmh,
                    "last_update": r.last_update.isoformat() if r.last_update else None,
                    "dispatch_incident": route.get("incident_id") if dispatch_mode in ("dispatch", "onscene") else None,
                    "dispatch_phase": dispatch_mode if dispatch_mode in ("dispatch", "onscene") else None,
                },
            }
        )
    return {
        "type": "FeatureCollection",
        "features": features,
        "count": len(features),
        "status_counts": counts,
    }


@router.get("/units")
async def live_units(db: AsyncSession = Depends(get_db)):
    """Devriye birimlerinin anlik konumu (GeoJSON) — polling istemcileri icin."""
    return await _units_payload(db)


@router.websocket("/ws/units")
async def ws_units(websocket: WebSocket):
    """Canli birim akisi: her tick'te GeoJSON gonderir (polling'e gerek kalmaz)."""
    await websocket.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                payload = await _units_payload(db)
            await websocket.send_json(payload)
            await asyncio.sleep(TICK_SECONDS)
    except (WebSocketDisconnect, RuntimeError):
        return


@router.get("/units/{unit_id}/history")
async def unit_track_history(
    unit_id: str,
    hours: int = Query(default=6, ge=1, le=72),
    db: AsyncSession = Depends(get_db),
):
    """Bir birimin gecmis rotasi (iz surme) — police_unit_history'den."""
    since = utcnow_naive() - timedelta(hours=hours)
    rows = (
        await db.execute(
            select(
                PoliceUnitHistory.status,
                PoliceUnitHistory.speed_kmh,
                PoliceUnitHistory.recorded_at,
                func.ST_X(PoliceUnitHistory.location).label("lon"),
                func.ST_Y(PoliceUnitHistory.location).label("lat"),
            )
            .where(PoliceUnitHistory.unit_id == unit_id, PoliceUnitHistory.recorded_at >= since)
            .order_by(PoliceUnitHistory.recorded_at.asc())
        )
    ).all()
    return {
        "unit_id": unit_id,
        "window_hours": hours,
        "point_count": len(rows),
        "track": [
            {
                "lat": float(r.lat), "lon": float(r.lon),
                "status": r.status, "speed_kmh": r.speed_kmh,
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in rows if r.lat is not None and r.lon is not None
        ],
    }


@router.post("/units/seed", dependencies=[Depends(require_admin)])
async def reseed_units(db: AsyncSession = Depends(get_db)):
    """Devriye birimlerini sifirlayip yeniden olusturur."""
    created = await seed_police_units(db, force=True)
    return {"status": "ok", "units_created": created}


# ---------------------------------------------------------------- analitik

async def _city_counts(db: AsyncSession, start, end) -> dict[str, int]:
    """Verilen zaman araliginda sehir basina olay sayisi."""
    rows = (
        await db.execute(
            select(CrimeEvent.city, func.count())
            .where(
                CrimeEvent.timestamp >= start,
                CrimeEvent.timestamp < end,
                CrimeEvent.city.isnot(None),
            )
            .group_by(CrimeEvent.city)
        )
    ).all()
    return {str(c).lower(): int(n) for c, n in rows if c}


@router.get("/analytics/trends")
async def crime_trends(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Son N gun vs onceki N gun — sehir bazinda yuzdesel degisim (Yukselen Risk Bolgeleri)."""
    cached = _cache_get(f"trends:{days}")
    if cached:
        return cached
    now = utcnow_naive()
    cur_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)

    current = await _city_counts(db, cur_start, now)
    previous = await _city_counts(db, prev_start, cur_start)

    zones = []
    for city in sorted(set(current) | set(previous)):
        cur, prev = current.get(city, 0), previous.get(city, 0)
        change_pct = pct_change(cur, prev)
        trend = (
            "rising" if change_pct >= RISING_THRESHOLD_PCT
            else "falling" if change_pct <= -RISING_THRESHOLD_PCT
            else "stable"
        )
        coords = CITY_COORDS.get(city)
        zones.append(
            {
                "city": city,
                "current_period": cur,
                "previous_period": prev,
                "change_pct": change_pct,
                "trend": trend,
                "per_100k": per_100k(cur, city),
                "lat": coords[0] if coords else None,
                "lon": coords[1] if coords else None,
            }
        )

    zones.sort(key=lambda z: z["change_pct"], reverse=True)
    return _cache_put(
        f"trends:{days}",
        {
            "period_days": days,
            "rising_threshold_pct": RISING_THRESHOLD_PCT,
            "rising_zones": [z for z in zones if z["trend"] == "rising"],
            "zones": zones,
        },
    )


@router.get("/analytics/predictive")
async def predictive_risk(
    hours_window: int = Query(default=3, ge=1, le=24, description="Guncel yogunluk penceresi (saat)"),
    baseline_days: int = Query(default=28, ge=7, le=60, description="Tarihsel taban penceresi (gun)"),
    db: AsyncSession = Depends(get_db),
):
    """Erken-uyari risk skoru: yogunluk sapmasi + 7g trend + siddet (bkz. predictive.py metodoloji notu)."""
    cache_key = f"predictive:{hours_window}:{baseline_days}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    now = utcnow_naive()
    recent_start = now - timedelta(hours=hours_window)
    baseline_start = now - timedelta(days=baseline_days)

    recent_counts = await _city_counts(db, recent_start, now)
    baseline_counts_incl = await _city_counts(db, baseline_start, now)
    baseline_counts = {
        c: baseline_counts_incl.get(c, 0) - recent_counts.get(c, 0) for c in baseline_counts_incl
    }
    trend_cur = await _city_counts(db, now - timedelta(days=7), now)
    trend_prev = await _city_counts(db, now - timedelta(days=14), now - timedelta(days=7))

    sev_rows = (
        await db.execute(
            select(CrimeEvent.city, func.avg(CrimeEvent.severity_score))
            .where(CrimeEvent.timestamp >= recent_start, CrimeEvent.city.isnot(None))
            .group_by(CrimeEvent.city)
        )
    ).all()
    avg_sev = {str(c).lower(): float(s or 0) for c, s in sev_rows if c}

    baseline_hours = max(baseline_days * 24 - hours_window, 1)
    cities = set(recent_counts) | {c for c, n in baseline_counts.items() if n > 0} | set(trend_cur)

    results = []
    for city in cities:
        trend_pct = pct_change(trend_cur.get(city, 0), trend_prev.get(city, 0))
        scored = compute_predictive_score(
            recent_count=recent_counts.get(city, 0),
            recent_hours=hours_window,
            baseline_count=max(baseline_counts.get(city, 0), 0),
            baseline_hours=baseline_hours,
            avg_severity_recent=avg_sev.get(city, 0.0),
            trend_pct=trend_pct,
        )
        coords = CITY_COORDS.get(city)
        results.append(
            {
                "city": city,
                "recent_count": recent_counts.get(city, 0),
                "trend_pct_7d": trend_pct,
                "lat": coords[0] if coords else None,
                "lon": coords[1] if coords else None,
                **scored,
            }
        )

    results.sort(key=lambda r: r["predictive_score"], reverse=True)
    return _cache_put(
        cache_key,
        {
            "hours_window": hours_window,
            "baseline_days": baseline_days,
            "generated_at": now.isoformat(),
            "methodology": "heuristic_v1",
            "methodology_note": "ML modeli degil; kurala dayali erken-uyari skoru (bkz. predictive.py)",
            "cities": results,
        },
    )


@router.get("/incidents/queue")
async def dispatch_queue(db: AsyncSession = Depends(get_db)):
    """Sevk kuyrugu: bekleyen + atanmis kritik olaylar, oncelik sirasiyla."""
    from app.modules.c4i.dispatch import DISPATCH_MIN_SEVERITY, DISPATCH_WINDOW_MIN, eta_minutes, haversine_km

    now = utcnow_naive()
    since = now - timedelta(minutes=DISPATCH_WINDOW_MIN)
    rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.severity_score,
                CrimeEvent.city,
                CrimeEvent.category,
                CrimeEvent.description,
                CrimeEvent.timestamp,
                CrimeEvent.assigned_unit_id,
                CrimeEvent.resolved_at,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(
                CrimeEvent.timestamp >= since,
                CrimeEvent.severity_score >= DISPATCH_MIN_SEVERITY,
                CrimeEvent.resolved_at.is_(None),
            )
        )
    ).all()

    unit_coords: dict[str, tuple[float, float]] = {}
    if any(r.assigned_unit_id for r in rows):
        unit_rows = (
            await db.execute(
                select(
                    PoliceUnit.unit_id,
                    func.ST_X(PoliceUnit.current_location).label("lon"),
                    func.ST_Y(PoliceUnit.current_location).label("lat"),
                ).where(PoliceUnit.current_location.isnot(None))
            )
        ).all()
        unit_coords = {u.unit_id: (float(u.lat), float(u.lon)) for u in unit_rows}

    items = []
    for r in rows:
        age_min = max((now - r.timestamp).total_seconds() / 60.0, 0.0) if r.timestamp else 0.0
        eta = None
        if r.assigned_unit_id and r.assigned_unit_id in unit_coords and r.lat is not None:
            u_lat, u_lon = unit_coords[r.assigned_unit_id]
            eta = eta_minutes(haversine_km(u_lat, u_lon, float(r.lat), float(r.lon)))
        items.append(
            {
                "id": r.id,
                "city": r.city,
                "category": r.category,
                "description": (r.description or "")[:160],
                "severity_score": r.severity_score,
                "age_minutes": round(age_min, 1),
                "priority": priority_score(float(r.severity_score or 0), age_min),
                "status": "assigned" if r.assigned_unit_id else "pending",
                "assigned_unit_id": r.assigned_unit_id,
                "eta_minutes": eta,
                "lat": float(r.lat) if r.lat is not None else None,
                "lon": float(r.lon) if r.lon is not None else None,
            }
        )
    items.sort(key=lambda x: x["priority"], reverse=True)
    return {
        "window_minutes": DISPATCH_WINDOW_MIN,
        "min_severity": DISPATCH_MIN_SEVERITY,
        "pending_count": sum(1 for i in items if i["status"] == "pending"),
        "assigned_count": sum(1 for i in items if i["status"] == "assigned"),
        "items": items,
    }


@router.post("/incidents/{incident_id}/resolve", dependencies=[Depends(require_admin)])
async def resolve_incident(incident_id: int, db: AsyncSession = Depends(get_db)):
    """Bir olayi manuel kapatir (sevkiyatci override) — atanmis birim varsa devriyeye doner."""
    now = utcnow_naive()
    result = await db.execute(
        update(CrimeEvent)
        .where(CrimeEvent.id == incident_id, CrimeEvent.resolved_at.is_(None))
        .values(resolved_at=now)
        .returning(CrimeEvent.assigned_unit_id)
    )
    row = result.first()
    if row is None:
        return {"status": "not_found_or_already_resolved", "incident_id": incident_id}

    assigned_unit_id = row[0]
    if assigned_unit_id:
        unit_row = (
            await db.execute(select(PoliceUnit).where(PoliceUnit.unit_id == assigned_unit_id))
        ).scalar_one_or_none()
        if unit_row and unit_row.status in ("responding",):
            route = unit_row.assigned_route or {}
            scene_lon = route.get("scene_lon") or (route.get("waypoints") or [[35.0, 39.0]])[-1][0]
            scene_lat = route.get("scene_lat") or (route.get("waypoints") or [[35.0, 39.0]])[-1][1]
            unit_row.status = "patrolling"
            unit_row.speed_kmh = 40.0
            from app.modules.c4i.simulation import _random_patrol_route

            unit_row.assigned_route = {
                "waypoints": _random_patrol_route(scene_lat, scene_lon, radius_deg=0.03),
                "leg": 0, "t": 0.0,
            }
    await db.commit()
    return {"status": "resolved", "incident_id": incident_id, "released_unit": assigned_unit_id}


@router.get("/analytics/critical")
async def critical_incidents(
    hours: int = Query(default=1, ge=1, le=48),
    min_severity: float = Query(default=7.0, ge=1.0, le=10.0),
    db: AsyncSession = Depends(get_db),
):
    """Son X saatteki kritik olaylar (varsayilan: 1 saat, siddet >= 7)."""
    since = utcnow_naive() - timedelta(hours=hours)
    rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.category,
                CrimeEvent.incident_type,
                CrimeEvent.severity_score,
                CrimeEvent.city,
                CrimeEvent.description,
                CrimeEvent.timestamp,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            )
            .where(CrimeEvent.timestamp >= since, CrimeEvent.severity_score >= min_severity)
            .order_by(CrimeEvent.severity_score.desc())
            .limit(50)
        )
    ).all()
    return {
        "window_hours": hours,
        "min_severity": min_severity,
        "count": len(rows),
        "incidents": [
            {
                "id": r.id,
                "category": r.category,
                "incident_type": r.incident_type,
                "severity_score": r.severity_score,
                "city": r.city,
                "description": (r.description or "")[:200],
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "lat": float(r.lat) if r.lat is not None else None,
                "lon": float(r.lon) if r.lon is not None else None,
            }
            for r in rows
        ],
    }


@router.get("/analytics/corridors")
async def high_risk_corridors(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Yuksek riskli koridorlar: son N gunde kritik olay yogunlugu en yuksek sehirler."""
    cached = _cache_get(f"corridors:{days}")
    if cached:
        return cached
    since = utcnow_naive() - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                CrimeEvent.city,
                func.count().label("n"),
                func.avg(CrimeEvent.severity_score).label("avg_sev"),
                func.max(CrimeEvent.severity_score).label("max_sev"),
            )
            .where(
                CrimeEvent.timestamp >= since,
                CrimeEvent.severity_score >= 6.0,
                CrimeEvent.city.isnot(None),
            )
            .group_by(CrimeEvent.city)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()

    corridors = []
    for r in rows:
        city = str(r.city).lower()
        coords = CITY_COORDS.get(city)
        risk_score = round(float(r.n) * float(r.avg_sev or 0) / 10.0, 1)
        corridors.append(
            {
                "city": city,
                "incident_count": int(r.n),
                "avg_severity": round(float(r.avg_sev or 0), 1),
                "max_severity": float(r.max_sev or 0),
                "risk_score": risk_score,
                "per_100k": per_100k(int(r.n), city),
                "lat": coords[0] if coords else None,
                "lon": coords[1] if coords else None,
            }
        )
    corridors.sort(key=lambda c: c["risk_score"], reverse=True)
    return _cache_put(f"corridors:{days}", {"period_days": days, "corridors": corridors})


# ---------------------------------------------------------------- performans KPI

@router.get("/analytics/performance")
async def dispatch_performance(
    days: int = Query(default=30, ge=1, le=180, description="Kapanan olaylarin geriye donuk penceresi"),
    db: AsyncSession = Depends(get_db),
):
    """Sevk gecikmesi / seyahat suresi / sahne suresi / toplam mudahale suresi KPI'lari.

    C4I sisteminin somut degerini gosterir: 'devriye agi olmadan once vs sonra ortalama
    mudahale suresi ne kadar' sorusuna sayisal cevap. Yalnizca en az bir zaman damgasi
    dolu olan (dispatched_at doluysa) olaylar dahil edilir.
    """
    cache_key = f"performance:{days}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    since = utcnow_naive() - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.city,
                CrimeEvent.assigned_unit_id,
                CrimeEvent.timestamp,
                CrimeEvent.dispatched_at,
                CrimeEvent.arrived_at,
                CrimeEvent.resolved_at,
            ).where(CrimeEvent.timestamp >= since, CrimeEvent.dispatched_at.isnot(None))
        )
    ).all()

    report = build_performance_report(rows)
    return _cache_put(cache_key, {"period_days": days, **report})


# ---------------------------------------------------------------- kapsama boslugu

@router.get("/analytics/coverage")
async def coverage_gaps(
    days: int = Query(default=30, ge=1, le=180),
    min_severity: float = Query(default=6.0, ge=1.0, le=10.0),
    db: AsyncSession = Depends(get_db),
):
    """Risk yuksek ama devriyeye uzak bolgeler — kaynak (devriye/karakol) yerlesim onerisi icin."""
    cache_key = f"coverage:{days}:{min_severity}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    since = utcnow_naive() - timedelta(days=days)
    inc_rows = (
        await db.execute(
            select(
                CrimeEvent.city,
                CrimeEvent.severity_score,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(
                CrimeEvent.timestamp >= since,
                CrimeEvent.severity_score >= min_severity,
                CrimeEvent.location.isnot(None),
            )
        )
    ).all()
    unit_rows = (
        await db.execute(
            select(
                func.ST_X(PoliceUnit.current_location).label("lon"),
                func.ST_Y(PoliceUnit.current_location).label("lat"),
            ).where(PoliceUnit.current_location.isnot(None), PoliceUnit.status != "offline")
        )
    ).all()

    incidents = [
        {"city": r.city, "lat": float(r.lat), "lon": float(r.lon), "severity_score": r.severity_score}
        for r in inc_rows
    ]
    units = [{"lat": float(u.lat), "lon": float(u.lon)} for u in unit_rows]

    report = compute_coverage_report(incidents, units)
    for g in report["gaps"]:
        coords = CITY_COORDS.get(g["city"])
        g["lat"] = coords[0] if coords else None
        g["lon"] = coords[1] if coords else None

    return _cache_put(
        cache_key,
        {
            "period_days": days,
            "min_severity": min_severity,
            "methodology_note": "Birimlerin GUNCEL konumu kullanilir, olay anindaki tarihsel konum degil.",
            **report,
        },
    )
