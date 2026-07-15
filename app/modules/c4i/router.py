"""C4I API: canli devriye takibi, trend analitigi, kritik olay akisi."""

from __future__ import annotations

import asyncio
import random
import time
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_optional_user, require_admin, require_write_access, scope_city_for
from app.core.database import AsyncSessionLocal, get_db
from app.modules.auth.security import verify_token
from app.modules.c4i.coverage import compute_coverage_report, nearest_unit_distance
from app.modules.c4i.dispatch import compute_required_units, priority_score
from app.modules.c4i.models import PoliceUnit, PoliceUnitHistory
from app.modules.c4i.performance import build_performance_report
from app.modules.c4i.predictive import compute_predictive_score
from app.modules.c4i.scorecard import build_scorecard
from app.modules.c4i.seasonal import compute_monthly_breakdown, compute_seasonal_risers
from app.modules.c4i.simulation import TICK_SECONDS, seed_police_units
from app.modules.crime.district_lookup import list_districts, resolve_district
from app.modules.crime.geometry_utils import crime_point_wkt, utcnow_naive
from app.modules.crime.models import CrimeEvent
from app.modules.crime.population import IL_LABELS_TR, per_100k
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


# ---------------------------------------------------------------- cografi referans

@router.get("/geo/cities")
async def geo_cities():
    """81 il listesi (ascii anahtar + Turkce goruntu adi), Turkce alfabetik siralanmis.

    Frontend'deki il/ilce filtre dropdown'lari eskiden yalnizca 11 buyuk sehri
    hardcode ediyordu (bkz. CLAUDE.md v2.8) — bu uc nokta tum 81 ili sunar.
    """
    cities = sorted(
        ({"city": city, "label": IL_LABELS_TR.get(city, city.title())} for city in CITY_COORDS),
        key=lambda c: c["label"],
    )
    return {"cities": cities}


@router.get("/geo/districts")
async def geo_districts(city: str = Query(...)):
    """Bir ilin bilinen ilce adlari (turkey-ilce.geojson kaynakli, alfabetik)."""
    city_norm = city.strip().lower()
    return {"city": city_norm, "districts": list_districts(city_norm)}


# ---------------------------------------------------------------- birimler

async def _units_payload(db: AsyncSession, scope_city: str | None = None) -> dict:
    """Devriye birimlerinin anlik GeoJSON'u — REST ve WebSocket ayni ciktiyi paylasir.

    scope_city verilirse (city_operator oturumu) yalnizca o ile ait birimler donulur —
    sunucu tarafinda zorunlu kilinan sehir kisitlamasi (istemci tarafi filtre degil).
    """
    conditions = [PoliceUnit.current_location.isnot(None)]
    if scope_city:
        conditions.append(func.lower(PoliceUnit.city) == scope_city)
    rows = (
        await db.execute(
            select(
                PoliceUnit.unit_id,
                PoliceUnit.unit_type,
                PoliceUnit.status,
                PoliceUnit.city,
                PoliceUnit.district,
                PoliceUnit.speed_kmh,
                PoliceUnit.last_update,
                PoliceUnit.assigned_route,
                func.ST_X(PoliceUnit.current_location).label("lon"),
                func.ST_Y(PoliceUnit.current_location).label("lat"),
            ).where(*conditions)
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
                    "district": r.district,
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
async def live_units(db: AsyncSession = Depends(get_db), user: dict | None = Depends(get_optional_user)):
    """Devriye birimlerinin anlik konumu (GeoJSON) — polling istemcileri icin."""
    return await _units_payload(db, scope_city=scope_city_for(user))


@router.websocket("/ws/units")
async def ws_units(websocket: WebSocket, token: str | None = Query(default=None)):
    """Canli birim akisi: her tick'te GeoJSON gonderir (polling'e gerek kalmaz).

    Tarayici WebSocket API'si custom header gonderemedigi icin oturum token'i query
    string'ten alinir (?token=...) — REST tarafinda Authorization header'i ile ayni islevi gorur.
    """
    await websocket.accept()
    user = verify_token(token) if token else None
    scope_city = scope_city_for(user)
    try:
        while True:
            async with AsyncSessionLocal() as db:
                payload = await _units_payload(db, scope_city=scope_city)
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


# ---------------------------------------------------------------- ihbar girisi

class IncidentReportRequest(BaseModel):
    """Cagri merkezi / dispatcher ihbar girisi — OSINT kazima degil, dogrudan giris kanali."""

    category: str
    incident_type: str = "crime"  # crime | traffic_accident | fire_anomaly
    severity_score: float = Field(default=5.0, ge=1.0, le=10.0)
    description: str | None = None
    city: str
    district: str | None = None
    # Bos birakilirsa sehir merkezi koordinati + hafif rastgele sapma kullanilir —
    # gercek sistemde adres geocoding'den gelecek, demo/erken evrede zorunlu degil.
    lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    lon: float | None = Field(default=None, ge=-180.0, le=180.0)


@router.post("/incidents/report")
async def report_incident(
    payload: IncidentReportRequest,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(require_write_access),
):
    """Gelen bir ihbari dogrudan crime_events'e dusurur (dispatch kuyrugu otomatik devreye girer).

    Bu, OSINT haber kazima hattindan (scraper.py) bagimsiz, cagri merkezi/155-156 tarzi
    ihbarlarin sisteme aninda girisini simule eden kanaldir (bkz. docs/PLAN_ASAYIS_PLATFORMU.md Faz 2).
    city_operator oturumu varsa il, kendi iline sabitlenir (baska il icin ihbar giremez).
    """
    scope_city = scope_city_for(user)
    city = scope_city or payload.city.strip().lower()
    lat, lon = payload.lat, payload.lon
    if lat is None or lon is None:
        coords = CITY_COORDS.get(city)
        if not coords:
            return {"status": "error", "detail": f"Bilinmeyen sehir '{city}' — lat/lon belirtilmeli."}
        base_lat, base_lon = coords
        lat = base_lat + random.uniform(-0.03, 0.03)
        lon = base_lon + random.uniform(-0.03, 0.03)

    district = (payload.district or "").strip() or resolve_district(city, lat, lon)

    now = utcnow_naive()
    event = CrimeEvent(
        category=payload.category.strip().lower(),
        incident_type=payload.incident_type,
        severity_score=payload.severity_score,
        description=payload.description,
        source="manual_ihbar",
        city=city,
        district=district,
        location=crime_point_wkt(lon, lat),
        timestamp=now,
        required_units=compute_required_units(payload.severity_score),
        assigned_unit_ids=[],
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {"status": "ok", "incident_id": event.id, "timestamp": now.isoformat()}


# ---------------------------------------------------------------- analitik

async def _city_counts(db: AsyncSession, start, end, scope_city: str | None = None) -> dict[str, int]:
    """Verilen zaman araliginda sehir basina olay sayisi (scope_city verilirse tek il)."""
    conditions = [CrimeEvent.timestamp >= start, CrimeEvent.timestamp < end, CrimeEvent.city.isnot(None)]
    if scope_city:
        conditions.append(func.lower(CrimeEvent.city) == scope_city)
    rows = (
        await db.execute(select(CrimeEvent.city, func.count()).where(*conditions).group_by(CrimeEvent.city))
    ).all()
    return {str(c).lower(): int(n) for c, n in rows if c}


@router.get("/analytics/trends")
async def crime_trends(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Son N gun vs onceki N gun — sehir bazinda yuzdesel degisim (Yukselen Risk Bolgeleri)."""
    scope_city = scope_city_for(user)
    cache_key = f"trends:{days}:{scope_city or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    now = utcnow_naive()
    cur_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)

    current = await _city_counts(db, cur_start, now, scope_city)
    previous = await _city_counts(db, prev_start, cur_start, scope_city)

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
        cache_key,
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
    user: dict | None = Depends(get_optional_user),
):
    """Erken-uyari risk skoru: yogunluk sapmasi + 7g trend + siddet (bkz. predictive.py metodoloji notu)."""
    scope_city = scope_city_for(user)
    cache_key = f"predictive:{hours_window}:{baseline_days}:{scope_city or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    now = utcnow_naive()
    recent_start = now - timedelta(hours=hours_window)
    baseline_start = now - timedelta(days=baseline_days)

    recent_counts = await _city_counts(db, recent_start, now, scope_city)
    baseline_counts_incl = await _city_counts(db, baseline_start, now, scope_city)
    baseline_counts = {
        c: baseline_counts_incl.get(c, 0) - recent_counts.get(c, 0) for c in baseline_counts_incl
    }
    trend_cur = await _city_counts(db, now - timedelta(days=7), now, scope_city)
    trend_prev = await _city_counts(db, now - timedelta(days=14), now - timedelta(days=7), scope_city)

    sev_conditions = [CrimeEvent.timestamp >= recent_start, CrimeEvent.city.isnot(None)]
    if scope_city:
        sev_conditions.append(func.lower(CrimeEvent.city) == scope_city)
    sev_rows = (
        await db.execute(
            select(CrimeEvent.city, func.avg(CrimeEvent.severity_score))
            .where(*sev_conditions)
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
async def dispatch_queue(db: AsyncSession = Depends(get_db), user: dict | None = Depends(get_optional_user)):
    """Sevk kuyrugu: bekleyen + atanmis kritik olaylar, oncelik sirasiyla."""
    from app.modules.c4i.dispatch import DISPATCH_MIN_SEVERITY, DISPATCH_WINDOW_MIN, eta_minutes, haversine_km

    scope_city = scope_city_for(user)
    now = utcnow_naive()
    since = now - timedelta(minutes=DISPATCH_WINDOW_MIN)
    conditions = [
        CrimeEvent.timestamp >= since,
        CrimeEvent.severity_score >= DISPATCH_MIN_SEVERITY,
        CrimeEvent.resolved_at.is_(None),
    ]
    if scope_city:
        conditions.append(func.lower(CrimeEvent.city) == scope_city)
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
                CrimeEvent.assigned_unit_ids,
                CrimeEvent.required_units,
                CrimeEvent.resolved_at,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(*conditions)
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
                "assigned_unit_ids": r.assigned_unit_ids or [],
                "required_units": r.required_units or 1,
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


@router.post("/incidents/{incident_id}/resolve")
async def resolve_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(require_write_access),
):
    """Bir olayi manuel kapatir (sevkiyatci override) — atanmis birim varsa devriyeye doner.

    city_operator oturumu varsa yalnizca kendi iline ait olaylari kapatabilir.
    """
    existing = (
        await db.execute(
            select(CrimeEvent.city, CrimeEvent.assigned_unit_id, CrimeEvent.assigned_unit_ids)
            .where(CrimeEvent.id == incident_id)
        )
    ).first()
    if existing is None:
        return {"status": "not_found_or_already_resolved", "incident_id": incident_id}
    owner, primary_unit_id, previously_assigned = existing
    scope_city = scope_city_for(user)
    if scope_city and (owner or "").strip().lower() != scope_city:
        raise HTTPException(status_code=403, detail="Bu olay sizin ilinize ait degil.")

    now = utcnow_naive()
    result = await db.execute(
        update(CrimeEvent)
        .where(CrimeEvent.id == incident_id, CrimeEvent.resolved_at.is_(None))
        .values(resolved_at=now)
        .returning(CrimeEvent.id)
    )
    if result.first() is None:
        return {"status": "not_found_or_already_resolved", "incident_id": incident_id}

    released_units = sorted(set(previously_assigned or []) | ({primary_unit_id} if primary_unit_id else set()))
    from app.modules.c4i.simulation import _random_patrol_route

    for unit_id in released_units:
        unit_row = (
            await db.execute(select(PoliceUnit).where(PoliceUnit.unit_id == unit_id))
        ).scalar_one_or_none()
        if unit_row and unit_row.status in ("responding",):
            route = unit_row.assigned_route or {}
            scene_lon = route.get("scene_lon") or (route.get("waypoints") or [[35.0, 39.0]])[-1][0]
            scene_lat = route.get("scene_lat") or (route.get("waypoints") or [[35.0, 39.0]])[-1][1]
            unit_row.status = "patrolling"
            unit_row.speed_kmh = 40.0
            unit_row.assigned_route = {
                "waypoints": _random_patrol_route(scene_lat, scene_lon, radius_deg=0.03),
                "leg": 0, "t": 0.0,
            }
    await db.commit()
    return {"status": "resolved", "incident_id": incident_id, "released_units": released_units}


@router.get("/analytics/critical")
async def critical_incidents(
    hours: int = Query(default=1, ge=1, le=48),
    min_severity: float = Query(default=7.0, ge=1.0, le=10.0),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Son X saatteki kritik olaylar (varsayilan: 1 saat, siddet >= 7)."""
    scope_city = scope_city_for(user)
    since = utcnow_naive() - timedelta(hours=hours)
    conditions = [CrimeEvent.timestamp >= since, CrimeEvent.severity_score >= min_severity]
    if scope_city:
        conditions.append(func.lower(CrimeEvent.city) == scope_city)
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
            .where(*conditions)
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
    user: dict | None = Depends(get_optional_user),
):
    """Yuksek riskli koridorlar: son N gunde kritik olay yogunlugu en yuksek sehirler."""
    scope_city = scope_city_for(user)
    cache_key = f"corridors:{days}:{scope_city or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    since = utcnow_naive() - timedelta(days=days)
    conditions = [CrimeEvent.timestamp >= since, CrimeEvent.severity_score >= 6.0, CrimeEvent.city.isnot(None)]
    if scope_city:
        conditions.append(func.lower(CrimeEvent.city) == scope_city)
    rows = (
        await db.execute(
            select(
                CrimeEvent.city,
                func.count().label("n"),
                func.avg(CrimeEvent.severity_score).label("avg_sev"),
                func.max(CrimeEvent.severity_score).label("max_sev"),
            )
            .where(*conditions)
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
    return _cache_put(cache_key, {"period_days": days, "corridors": corridors})


# ---------------------------------------------------------------- performans KPI

@router.get("/analytics/performance")
async def dispatch_performance(
    days: int = Query(default=30, ge=1, le=180, description="Kapanan olaylarin geriye donuk penceresi"),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Sevk gecikmesi / seyahat suresi / sahne suresi / toplam mudahale suresi KPI'lari.

    C4I sisteminin somut degerini gosterir: 'devriye agi olmadan once vs sonra ortalama
    mudahale suresi ne kadar' sorusuna sayisal cevap. Yalnizca en az bir zaman damgasi
    dolu olan (dispatched_at doluysa) olaylar dahil edilir.
    """
    scope_city = scope_city_for(user)
    cache_key = f"performance:{days}:{scope_city or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    since = utcnow_naive() - timedelta(days=days)
    conditions = [CrimeEvent.timestamp >= since, CrimeEvent.dispatched_at.isnot(None)]
    if scope_city:
        conditions.append(func.lower(CrimeEvent.city) == scope_city)
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
            ).where(*conditions)
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
    user: dict | None = Depends(get_optional_user),
):
    """Risk yuksek ama devriyeye uzak bolgeler — kaynak (devriye/karakol) yerlesim onerisi icin."""
    scope_city = scope_city_for(user)
    cache_key = f"coverage:{days}:{min_severity}:{scope_city or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    since = utcnow_naive() - timedelta(days=days)
    inc_conditions = [
        CrimeEvent.timestamp >= since,
        CrimeEvent.severity_score >= min_severity,
        CrimeEvent.location.isnot(None),
    ]
    unit_conditions = [PoliceUnit.current_location.isnot(None), PoliceUnit.status != "offline"]
    if scope_city:
        inc_conditions.append(func.lower(CrimeEvent.city) == scope_city)
        unit_conditions.append(func.lower(PoliceUnit.city) == scope_city)
    inc_rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.city,
                CrimeEvent.severity_score,
                CrimeEvent.timestamp,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(*inc_conditions)
        )
    ).all()
    unit_rows = (
        await db.execute(
            select(
                func.ST_X(PoliceUnit.current_location).label("lon"),
                func.ST_Y(PoliceUnit.current_location).label("lat"),
            ).where(*unit_conditions)
        )
    ).all()
    units = [{"lat": float(u.lat), "lon": float(u.lon)} for u in unit_rows]

    # Tarihsel eslestirme: her olay icin, olay ANINDAN once kaydedilmis en son birim
    # konumlari (police_unit_history, "asof" — DISTINCT ON ile birim basina en yakin
    # onceki kayit). Hic tarihsel kaydi olmayan olaylar (ör. birim henuz yoktu / retention
    # disinda) GUNCEL konuma duser (compute_coverage_report distance_km=None gorunce
    # otomatik olarak 'units' parametresini kullanir).
    incident_ids = [r.id for r in inc_rows]
    history_by_incident: dict[int, list[tuple[float, float]]] = {}
    if incident_ids:
        hist_rows = (
            await db.execute(
                text(
                    """
                    SELECT inc.id AS incident_id, hist.unit_lat, hist.unit_lon
                    FROM (SELECT id, "timestamp" FROM crime_events WHERE id = ANY(:ids)) inc
                    CROSS JOIN LATERAL (
                        SELECT DISTINCT ON (unit_id)
                            ST_Y(location) AS unit_lat, ST_X(location) AS unit_lon
                        FROM police_unit_history
                        WHERE unit_id IS NOT NULL
                          AND recorded_at <= inc."timestamp"
                          AND location IS NOT NULL
                        ORDER BY unit_id, recorded_at DESC
                    ) hist
                    """
                ),
                {"ids": incident_ids},
            )
        ).all()
        for hr in hist_rows:
            history_by_incident.setdefault(hr.incident_id, []).append((float(hr.unit_lat), float(hr.unit_lon)))

    fallback_count = 0
    incidents = []
    for r in inc_rows:
        hist_units = history_by_incident.get(r.id)
        dist = nearest_unit_distance(float(r.lat), float(r.lon), hist_units) if hist_units else None
        if dist is None:
            fallback_count += 1
        incidents.append(
            {
                "city": r.city,
                "lat": float(r.lat),
                "lon": float(r.lon),
                "severity_score": r.severity_score,
                "distance_km": dist,
            }
        )

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
            "historical_match_count": len(incidents) - fallback_count,
            "current_position_fallback_count": fallback_count,
            "methodology_note": (
                "Olaylarin coguna police_unit_history'den olay anindaki (tarihsel) birim "
                "konumu eslestirildi; tarihsel kaydi olmayan olaylar guncel konuma dustu "
                "(bkz. current_position_fallback_count)."
            ),
            **report,
        },
    )


# ---------------------------------------------------------------- bolge kirilimi

@router.get("/analytics/breakdown")
async def region_breakdown(
    city: str | None = Query(default=None),
    district: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Secili il/ilce icin suc turu ve olay tipi dagilimi.

    Amasya -> Merzifon senaryosu icin: 'bu ilcede hangi suc turu / trafik kazasi
    ne kadar yogun' sorusuna cevap (bkz. docs/PLAN_ASAYIS_PLATFORMU.md Faz 4).
    city_operator oturumu varsa city parametresi kendi iline sabitlenir.
    """
    scope_city = scope_city_for(user)
    if scope_city:
        city = scope_city
    since = utcnow_naive() - timedelta(days=days)
    conditions = [CrimeEvent.timestamp >= since]
    if city:
        conditions.append(func.lower(CrimeEvent.city) == city.strip().lower())
    if district:
        conditions.append(func.lower(CrimeEvent.district) == district.strip().lower())

    total_row = (
        await db.execute(select(func.count(), func.avg(CrimeEvent.severity_score)).where(*conditions))
    ).one()
    total, avg_sev = int(total_row[0] or 0), float(total_row[1] or 0)

    cat_rows = (
        await db.execute(
            select(CrimeEvent.category, func.count())
            .where(*conditions)
            .group_by(CrimeEvent.category)
            .order_by(func.count().desc())
            .limit(12)
        )
    ).all()
    type_rows = (
        await db.execute(
            select(CrimeEvent.incident_type, func.count()).where(*conditions).group_by(CrimeEvent.incident_type)
        )
    ).all()

    return {
        "city": city,
        "district": district,
        "period_days": days,
        "total": total,
        "avg_severity": round(avg_sev, 1),
        "categories": [{"category": c or "diger", "count": int(n)} for c, n in cat_rows],
        "incident_types": {(t or "crime"): int(n) for t, n in type_rows},
    }


@router.get("/analytics/districts")
async def district_listing(
    city: str = Query(...),
    days: int = Query(default=30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Secili ildeki ilceler icin olay + devriye ozet listesi (ilce bazli listeleme).

    Her ilce icin olay sayisi/ort. siddet (crime_events.district) ve aktif devriye
    sayisi (police_units.district) yan yana gosterilir — hangi ilcenin devriyeye
    gore olay yogunlugu yuksek oldugunu tek bakista gorebilmek icin.
    city_operator oturumu varsa city parametresi kendi iline sabitlenir.
    """
    scope_city = scope_city_for(user)
    since = utcnow_naive() - timedelta(days=days)
    city_norm = scope_city or city.strip().lower()

    inc_rows = (
        await db.execute(
            select(CrimeEvent.district, func.count(), func.avg(CrimeEvent.severity_score))
            .where(
                CrimeEvent.timestamp >= since,
                func.lower(CrimeEvent.city) == city_norm,
                CrimeEvent.district.isnot(None),
            )
            .group_by(CrimeEvent.district)
        )
    ).all()
    unit_rows = (
        await db.execute(
            select(PoliceUnit.district, func.count())
            .where(
                func.lower(PoliceUnit.city) == city_norm,
                PoliceUnit.district.isnot(None),
                PoliceUnit.status != "offline",
            )
            .group_by(PoliceUnit.district)
        )
    ).all()

    inc_map = {d: (int(n), round(float(s or 0), 1)) for d, n, s in inc_rows}
    unit_map = {d: int(n) for d, n in unit_rows}

    items = []
    for d in sorted(set(inc_map) | set(unit_map)):
        n, avg_sev = inc_map.get(d, (0, 0.0))
        items.append(
            {
                "district": d,
                "incident_count": n,
                "avg_severity": avg_sev,
                "patrol_unit_count": unit_map.get(d, 0),
            }
        )
    items.sort(key=lambda x: x["incident_count"], reverse=True)
    return {"city": city_norm, "period_days": days, "districts": items}


# ---------------------------------------------------------------- guvenlik puan karti

@router.get("/analytics/scorecard", dependencies=[Depends(require_admin)])
async def security_scorecard(
    days: int = Query(default=30, ge=1, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Sehirler arasi karsilastirmali guvenlik puan karti (mudahale suresi + kapsama + trend).

    Yalnizca admin gorur — city_operator zaten kendi ilini diger panellerde goruyor,
    baska illerle karsilastirma admin yetkisi gerektirir (bkz. app/modules/c4i/scorecard.py).
    """
    cache_key = f"scorecard:{days}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    since = utcnow_naive() - timedelta(days=days)

    perf_rows = (
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
    perf_report = build_performance_report(perf_rows)

    inc_rows = (
        await db.execute(
            select(
                CrimeEvent.city,
                CrimeEvent.severity_score,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(
                CrimeEvent.timestamp >= since,
                CrimeEvent.severity_score >= 6.0,
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
    coverage_report = compute_coverage_report(incidents, units, top_n=100)

    now = utcnow_naive()
    current = await _city_counts(db, now - timedelta(days=7), now)
    previous = await _city_counts(db, now - timedelta(days=14), now - timedelta(days=7))
    trend_zones = [
        {"city": city, "change_pct": pct_change(current.get(city, 0), previous.get(city, 0)), "current_period": current.get(city, 0)}
        for city in sorted(set(current) | set(previous))
    ]

    scorecard = build_scorecard(perf_report["by_city"], coverage_report["gaps"], trend_zones)
    return _cache_put(
        cache_key,
        {
            "period_days": days,
            "methodology_note": (
                "risk_index bilimsel kesin bir skor degildir — mudahale suresi + kapsama "
                "boslugu + trend'in agirlikli toplami, sehirleri hizli karsilastirmak icindir."
            ),
            "cities": scorecard,
        },
    )


# ---------------------------------------------------------------- mevsimsel istatistik

@router.get("/analytics/seasonal")
async def seasonal_stats(
    city: str | None = Query(default=None),
    group_by: str = Query(default="category", pattern="^(category|city)$"),
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Gecmis olaylardan aylik dagilim + yaz aylari (Haz-Agu) karsilastirmasi.

    'Mevsimsellik' degil, mevcut veri setinin aylik dagilimidir (bkz. seasonal.py metodoloji
    notu) — kural-tabanli, seffaf; ML tahmini degildir. city_operator oturumu varsa city
    kendi iline sabitlenir ve group_by zorla 'category' olur (tek il gorunumunde sehir
    kirilimi anlamsizdir).
    """
    scope_city = scope_city_for(user)
    if scope_city:
        city = scope_city
        group_by = "category"

    cache_key = f"seasonal:{city or 'all'}:{group_by}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    conditions = [CrimeEvent.timestamp.isnot(None)]
    if city:
        conditions.append(func.lower(CrimeEvent.city) == city.strip().lower())

    rows = (
        await db.execute(
            select(
                func.extract("month", CrimeEvent.timestamp).label("month"),
                CrimeEvent.category,
                CrimeEvent.city,
                CrimeEvent.severity_score,
            ).where(*conditions)
        )
    ).all()

    monthly = compute_monthly_breakdown(rows)
    risers = compute_seasonal_risers(rows, group_key=group_by)

    return _cache_put(
        cache_key,
        {
            "group_by": group_by,
            "city_filter": city,
            "total_incidents": len(rows),
            "methodology_note": (
                "Mevsimsellik degil, mevcut veri setinin aylik dagilimidir — guvenilir "
                "mevsimsel dongu tespiti icin birden fazla yilin verisi gerekir."
            ),
            "monthly_breakdown": monthly,
            "summer_risers": [r for r in risers if r["is_summer_riser"]][:10],
            "all_groups": risers[:20],
        },
    )
