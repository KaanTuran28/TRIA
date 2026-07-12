"""Devriye simulasyonu: police_units kayitlarini rota uzerinde hareket ettirir.

Gercek sistemde bu katman araclardaki GPS/AVL biriminden beslenir; simulasyon
ayni API sozlesmesini kullanarak sahte telemetri uretir.
"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.modules.c4i.models import PoliceUnit, PoliceUnitHistory
from app.modules.crime.models import CrimeEvent
from app.modules.crime.services import CITY_COORDS

logger = logging.getLogger("tria.c4i.simulation")

TICK_SECONDS = 3.0
DEG_PER_KM = 1.0 / 111.0
RESPONSE_SPEED_KMH_DEFAULT = 90.0

# Sehir basina birim sayisi (buyuk iller daha yogun devriye alir)
SEED_PLAN = {
    "istanbul": 6,
    "ankara": 4,
    "izmir": 3,
    "bursa": 2,
    "antalya": 2,
    "adana": 2,
    "gaziantep": 2,
    "konya": 1,
    "diyarbakir": 1,
    "trabzon": 1,
}

PLATE_CODES = {
    "istanbul": "34", "ankara": "06", "izmir": "35", "bursa": "16",
    "antalya": "07", "adana": "01", "gaziantep": "27", "konya": "42",
    "diyarbakir": "21", "trabzon": "61",
}


def _random_patrol_route(lat: float, lon: float, n_points: int = 6, radius_deg: float = 0.06) -> list[list[float]]:
    """Sehir merkezi cevresinde kapali devriye rotasi (lon, lat cifti listesi)."""
    pts = []
    for i in range(n_points):
        ang = (2 * math.pi * i / n_points) + random.uniform(-0.3, 0.3)
        r = radius_deg * random.uniform(0.4, 1.0)
        pts.append([round(lon + r * math.cos(ang), 6), round(lat + r * math.sin(ang), 6)])
    pts.append(pts[0])  # kapali dongu
    return pts


async def seed_police_units(db: AsyncSession, force: bool = False) -> int:
    """Tablo bossa (veya force ile) devriye birimlerini olusturur."""
    existing = (await db.execute(select(func.count()).select_from(PoliceUnit))).scalar_one()
    if existing and not force:
        return 0
    if force:
        await db.execute(text("DELETE FROM police_units"))

    created = 0
    for city, n_units in SEED_PLAN.items():
        coords = CITY_COORDS.get(city)
        if not coords:
            continue
        lat, lon = coords
        plate = PLATE_CODES.get(city, "00")
        for i in range(n_units):
            route = _random_patrol_route(lat, lon)
            start = route[0]
            unit = PoliceUnit(
                unit_id=f"EKIP-{plate}-{i + 1:02d}",
                unit_type="patrol_car" if i % 3 != 2 else "motorcycle",
                status="patrolling",
                city=city,
                current_location=f"SRID=4326;POINT({start[0]} {start[1]})",
                assigned_route={"waypoints": route, "leg": 0, "t": 0.0},
                speed_kmh=random.choice([35.0, 40.0, 45.0]),
            )
            db.add(unit)
            created += 1
    await db.commit()
    logger.info("C4I: %s devriye birimi olusturuldu", created)
    return created


def _advance_along_route(route: dict, speed_kmh: float, dt_s: float) -> tuple[dict, float, float]:
    """Rota durumunu dt kadar ilerletir; yeni (route, lon, lat) dondurur.

    mode="dispatch" rotalari hedefte durur (son noktada t=1.0 kalir);
    devriye rotalari kapali dongu olarak bastan sarar.
    """
    wps = route.get("waypoints") or []
    if len(wps) < 2:
        wp = wps[0] if wps else [35.0, 39.0]
        return route, wp[0], wp[1]

    is_dispatch = route.get("mode") == "dispatch"
    n_legs = len(wps) - 1
    leg = int(route.get("leg", 0)) % n_legs
    t = float(route.get("t", 0.0))
    remaining_deg = speed_kmh * (dt_s / 3600.0) * DEG_PER_KM  # km -> derece

    while remaining_deg > 0:
        a, b = wps[leg], wps[leg + 1]
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        left_on_seg = (1.0 - t) * seg_len
        if remaining_deg < left_on_seg:
            t += remaining_deg / seg_len
            remaining_deg = 0
        elif is_dispatch and leg == n_legs - 1:
            t = 1.0  # hedefe varildi
            remaining_deg = 0
        else:
            remaining_deg -= left_on_seg
            leg = (leg + 1) % n_legs
            t = 0.0

    a, b = wps[leg], wps[leg + 1]
    lon = a[0] + (b[0] - a[0]) * t
    lat = a[1] + (b[1] - a[1]) * t
    out = {**route, "waypoints": wps, "leg": leg, "t": round(t, 4)}
    return out, lon, lat


def _route_arrived(route: dict) -> bool:
    wps = route.get("waypoints") or []
    if len(wps) < 2:
        return True
    return int(route.get("leg", 0)) >= len(wps) - 2 and float(route.get("t", 0.0)) >= 0.999


def _maybe_flip_status(status: str) -> tuple[str, float]:
    """Durum gecisleri: devriye <-> mudahale, nadiren cevrimdisi."""
    r = random.random()
    if status == "patrolling":
        if r < 0.015:
            return "responding", 90.0
        if r < 0.017:
            return "offline", 0.0
        return "patrolling", random.choice([35.0, 40.0, 45.0])
    if status == "responding":
        if r < 0.08:
            return "patrolling", 40.0
        return "responding", 90.0
    # offline
    if r < 0.10:
        return "patrolling", 40.0
    return "offline", 0.0


_tick_counter = 0
DISPATCH_SWEEP_EVERY_N_TICKS = 5  # ~15 sn'de bir kritik olay taramasi
ONSCENE_DWELL_RANGE_S = (45.0, 150.0)  # olay yerinde gecirilen sure (mudahale suresi)


async def simulation_tick() -> None:
    """APScheduler tarafindan birkac saniyede bir cagrilir; birimleri hareket ettirir.

    Devriye birimleri uc modda olabilir:
    - patrol (varsayilan): kapali dongu rotada rastgele durum gecisleriyle dolasir
    - dispatch: kritik olaya dogru sabit hizla ilerler (bkz. dispatch.py)
    - onscene: olay yerine varmis, ONSCENE_DWELL_RANGE_S kadar sabit bekler, sonra
      crime_events.resolved_at doldurulur ve birim yeniden devriyeye doner
    """
    global _tick_counter
    _tick_counter += 1
    try:
        async with AsyncSessionLocal() as db:
            units = (await db.execute(select(PoliceUnit))).scalars().all()
            if not units:
                return
            now = datetime.utcnow()
            for unit in units:
                route_dict = dict(unit.assigned_route) if unit.assigned_route else {}
                mode = route_dict.get("mode")

                if mode == "onscene":
                    dwell_until = route_dict.get("dwell_until")
                    if dwell_until and now.isoformat() < dwell_until:
                        continue  # sahnede bekliyor, konum sabit
                    incident_id = route_dict.get("incident_id")
                    if incident_id:
                        await db.execute(
                            update(CrimeEvent)
                            .where(CrimeEvent.id == incident_id, CrimeEvent.resolved_at.is_(None))
                            .values(resolved_at=now)
                        )
                        logger.info("C4I: %s olayi kapatti (#%s), devriyeye dondu", unit.unit_id, incident_id)
                    unit.status = "patrolling"
                    unit.speed_kmh = 40.0
                    unit.assigned_route = {
                        "waypoints": _random_patrol_route(route_dict["scene_lat"], route_dict["scene_lon"], radius_deg=0.03),
                        "leg": 0, "t": 0.0,
                    }
                    unit.last_update = now
                    continue

                is_dispatch = mode == "dispatch"
                if is_dispatch:
                    speed = unit.speed_kmh or RESPONSE_SPEED_KMH_DEFAULT
                else:
                    new_status, speed = _maybe_flip_status(unit.status or "patrolling")
                    unit.status = new_status
                    unit.speed_kmh = speed
                if unit.status == "offline" or not route_dict:
                    continue

                route, lon, lat = _advance_along_route(route_dict, speed, TICK_SECONDS)
                if is_dispatch and _route_arrived(route):
                    # Olay yerine varildi: mudahale suresi (dwell) baslar
                    dwell_s = random.uniform(*ONSCENE_DWELL_RANGE_S)
                    route = {
                        **route,
                        "mode": "onscene",
                        "scene_lon": lon,
                        "scene_lat": lat,
                        "dwell_until": (now + timedelta(seconds=dwell_s)).isoformat(),
                    }
                    unit.status = "responding"
                    unit.speed_kmh = 0.0
                    incident_id = route_dict.get("incident_id")
                    if incident_id:
                        await db.execute(
                            update(CrimeEvent)
                            .where(CrimeEvent.id == incident_id, CrimeEvent.arrived_at.is_(None))
                            .values(arrived_at=now)
                        )
                    logger.info("C4I: %s olay yerine ulasti (#%s), mudahale basladi (~%.0f sn)",
                                unit.unit_id, incident_id, dwell_s)
                unit.assigned_route = route
                unit.current_location = f"SRID=4326;POINT({round(lon, 6)} {round(lat, 6)})"
                unit.last_update = now
            await db.commit()

            if _tick_counter % DISPATCH_SWEEP_EVERY_N_TICKS == 0:
                from app.modules.c4i.dispatch import auto_dispatch

                await auto_dispatch(db)
    except Exception as exc:  # simulasyon hatasi uygulamayi dusurmemeli
        logger.warning("C4I simulasyon tick hatasi: %s", exc)


HISTORY_SNAPSHOT_INTERVAL_S = 60
HISTORY_RETENTION_DAYS = 30
_cleanup_counter = 0


async def snapshot_unit_history() -> None:
    """Birim konumlarinin periyodik anlik goruntusunu alir (iz surme icin).

    3 sn'lik tick'ten ayri, daha seyrek calisir (varsayilan 60 sn) —
    her tick'i kaydetmek tabloyu gereksiz sisirir.
    """
    global _cleanup_counter
    _cleanup_counter += 1
    try:
        async with AsyncSessionLocal() as db:
            units = (
                await db.execute(
                    select(
                        PoliceUnit.unit_id,
                        PoliceUnit.status,
                        PoliceUnit.speed_kmh,
                        PoliceUnit.current_location,
                    ).where(PoliceUnit.current_location.isnot(None))
                )
            ).all()
            now = datetime.utcnow()
            for u in units:
                db.add(
                    PoliceUnitHistory(
                        unit_id=u.unit_id,
                        status=u.status,
                        speed_kmh=u.speed_kmh,
                        location=u.current_location,
                        recorded_at=now,
                    )
                )
            await db.commit()

            # Saatte bir eski kayitlari temizle (retention)
            if _cleanup_counter % 60 == 0:
                cutoff = now - timedelta(days=HISTORY_RETENTION_DAYS)
                await db.execute(
                    text("DELETE FROM police_unit_history WHERE recorded_at < :cutoff"),
                    {"cutoff": cutoff},
                )
                await db.commit()
    except Exception as exc:
        logger.warning("C4I gecmis snapshot hatasi: %s", exc)
