"""
Mevcut crime_events kayitlarini normalize eder ve Turkiye disi konumlari duzeltir.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.crime.district_lookup import resolve_district
from app.modules.crime.geolocation import (
    is_in_turkey,
    normalize_category,
    resolve_crime_coordinates,
)
from app.modules.crime.geometry_utils import crime_point_wkt
from app.modules.crime.models import CrimeEvent

logger = logging.getLogger(__name__)


async def normalize_crime_database(db: AsyncSession) -> dict:
    rows = (
        await db.execute(
            select(
                CrimeEvent.id,
                CrimeEvent.category,
                CrimeEvent.description,
                CrimeEvent.city,
                CrimeEvent.district,
                func.ST_X(CrimeEvent.location).label("lon"),
                func.ST_Y(CrimeEvent.location).label("lat"),
            ).where(CrimeEvent.location.isnot(None))
        )
    ).all()

    stats = {
        "scanned": len(rows),
        "category_updated": 0,
        "location_fixed": 0,
        "district_filled": 0,
        "deleted": 0,
    }
    delete_ids: list[int] = []

    for row in rows:
        cat = normalize_category(row.category)
        if cat is None:
            delete_ids.append(row.id)
            stats["deleted"] += 1
            continue

        desc = row.description or ""
        geo = resolve_crime_coordinates(
            title=desc[:200],
            body=desc,
            city_hint=row.city,
            lat=float(row.lat) if row.lat is not None else None,
            lon=float(row.lon) if row.lon is not None else None,
        )

        if not geo:
            if row.lat is not None and row.lon is not None and not is_in_turkey(
                float(row.lat), float(row.lon)
            ):
                delete_ids.append(row.id)
                stats["deleted"] += 1
            continue

        stored = (row.category or "").strip()
        needs_cat = cat != stored and cat != stored.lower()
        needs_loc = (
            abs(float(row.lat) - geo["lat"]) > 0.01
            or abs(float(row.lon) - geo["lon"]) > 0.01
            or (row.city or "") != (geo["city"] or "")
        )
        district = row.district or resolve_district(geo["city"], geo["lat"], geo["lon"])
        needs_district = district and district != row.district

        if needs_cat or needs_loc or needs_district:
            wkt = crime_point_wkt(geo["lon"], geo["lat"])
            await db.execute(
                text(
                    """
                    UPDATE crime_events
                    SET category = :category,
                        city = :city,
                        district = :district,
                        location = ST_GeomFromEWKT(:wkt)
                    WHERE id = :id
                    """
                ),
                {
                    "id": row.id,
                    "category": cat,
                    "city": geo["city"],
                    "district": district,
                    "wkt": wkt,
                },
            )
            if needs_cat:
                stats["category_updated"] += 1
            if needs_loc:
                stats["location_fixed"] += 1
            if needs_district:
                stats["district_filled"] += 1

    if delete_ids:
        await db.execute(delete(CrimeEvent).where(CrimeEvent.id.in_(delete_ids)))

    await db.commit()
    logger.info("DB normalize: %s", stats)
    return stats
