"""Otomatik sevk (dispatch): kritik olaylara oncelik sirasiyla en yakin devriyeyi yonlendirir.

Durum DB'de tutulur (crime_events.assigned_unit_id / resolved_at) — surec-ici bellek
kullanilmaz, boylece restart veya coklu worker senaryosunda tutarlilik korunur.

Oncelik kurali: siddet puani + bekleme suresi bonusu (starvation'i onlemek icin —
dusuk siddetli ama uzun suredir bekleyen bir olay da zamanla siraya yukselir).
"""

from __future__ import annotations

import logging
import math
from datetime import timedelta

from sqlalchemy import func, select, update

from app.modules.c4i.models import PoliceUnit
from app.modules.crime.geometry_utils import utcnow_naive
from app.modules.crime.models import CrimeEvent

logger = logging.getLogger("tria.c4i.dispatch")

DISPATCH_MIN_SEVERITY = 7.0
DISPATCH_WINDOW_MIN = 30
MAX_DISPATCH_PER_SWEEP = 3
RESPONSE_SPEED_KMH = 90.0
AGE_BONUS_PER_5MIN = 0.5  # her 5 dk bekleme +0.5 oncelik puani (starvation onleme)
AGE_BONUS_CAP = 3.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def eta_minutes(distance_km: float, speed_kmh: float = RESPONSE_SPEED_KMH) -> float:
    return round(distance_km / max(speed_kmh, 1.0) * 60.0, 1)


def priority_score(severity: float, age_minutes: float) -> float:
    """Siddet + bekleme bonusu; starvation'i onlemek icin uzun bekleyen olay yukselir."""
    age_bonus = min(age_minutes / 5.0 * AGE_BONUS_PER_5MIN, AGE_BONUS_CAP)
    return round(severity + age_bonus, 2)


def nearest_unit(units: list, lat: float, lon: float):
    """(id, unit_id, lon, lat) satirlarindan en yakinini dondurur (None olabilir)."""
    best, best_km = None, float("inf")
    for u in units:
        km = haversine_km(lat, lon, float(u.lat), float(u.lon))
        if km < best_km:
            best, best_km = u, km
    return best, best_km


async def auto_dispatch(db) -> int:
    """Bekleyen kritik olaylara oncelik sirasiyla birim atar; atanan sayisini dondurur."""
    now = utcnow_naive()
    since = now - timedelta(minutes=DISPATCH_WINDOW_MIN)
    pending = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.severity_score,
                CrimeEvent.city,
                CrimeEvent.timestamp,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(
                CrimeEvent.timestamp >= since,
                CrimeEvent.severity_score >= DISPATCH_MIN_SEVERITY,
                CrimeEvent.location.isnot(None),
                CrimeEvent.assigned_unit_id.is_(None),
                CrimeEvent.resolved_at.is_(None),
            )
        )
    ).all()
    if not pending:
        return 0

    def age_min(ts) -> float:
        return max((now - ts).total_seconds() / 60.0, 0.0) if ts else 0.0

    ranked = sorted(
        pending,
        key=lambda e: priority_score(float(e.severity_score or 0), age_min(e.timestamp)),
        reverse=True,
    )

    available = list(
        (
            await db.execute(
                select(
                    PoliceUnit.id,
                    PoliceUnit.unit_id,
                    func.ST_X(PoliceUnit.current_location).label("lon"),
                    func.ST_Y(PoliceUnit.current_location).label("lat"),
                ).where(
                    PoliceUnit.status == "patrolling",
                    PoliceUnit.current_location.isnot(None),
                )
            )
        ).all()
    )

    dispatched = 0
    for event in ranked[:MAX_DISPATCH_PER_SWEEP]:
        if not available:
            break
        unit, distance_km = nearest_unit(available, float(event.lat), float(event.lon))
        if unit is None:
            break
        available = [u for u in available if u.id != unit.id]

        # Atomik atama: baska bir sweep/worker araya girdiyse (assigned_unit_id artik NULL degilse) atlanir.
        result = await db.execute(
            update(CrimeEvent)
            .where(CrimeEvent.id == event.id, CrimeEvent.assigned_unit_id.is_(None))
            .values(assigned_unit_id=unit.unit_id, dispatched_at=now)
        )
        if not result.rowcount:
            continue

        route = {
            "waypoints": [
                [round(float(unit.lon), 6), round(float(unit.lat), 6)],
                [round(float(event.lon), 6), round(float(event.lat), 6)],
            ],
            "leg": 0,
            "t": 0.0,
            "mode": "dispatch",
            "incident_id": int(event.id),
        }
        await db.execute(
            update(PoliceUnit)
            .where(PoliceUnit.id == unit.id)
            .values(status="responding", speed_kmh=RESPONSE_SPEED_KMH, assigned_route=route)
        )
        dispatched += 1
        logger.info(
            "DISPATCH: %s -> olay #%s (%.1f km, ETA %.1f dk, siddet %.1f, oncelik %.1f, %s)",
            unit.unit_id, event.id, distance_km, eta_minutes(distance_km),
            event.severity_score, priority_score(float(event.severity_score or 0), age_min(event.timestamp)),
            event.city,
        )

    if dispatched:
        await db.commit()
    return dispatched
