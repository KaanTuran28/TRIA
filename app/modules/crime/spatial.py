"""PostGIS uzamsal sorgu: cizilen alan icindeki olaylar."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.crime.geojson_utils import rows_to_feature_collection
from app.modules.crime.models import CrimeEvent

router = APIRouter(prefix="/api/v1", tags=["API v1"])


class SpatialSearchRequest(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Geometry (Polygon, Point+circle)")
    radius_m: float | None = Field(default=None, description="Daire yaricapi (metre)")


def _base_select():
    return select(
        CrimeEvent.id,
        CrimeEvent.category,
        CrimeEvent.severity_score,
        CrimeEvent.description,
        CrimeEvent.source,
        CrimeEvent.city,
        CrimeEvent.timestamp,
        func.ST_X(CrimeEvent.location).label("lon"),
        func.ST_Y(CrimeEvent.location).label("lat"),
    ).where(CrimeEvent.location.isnot(None))


@router.post("/incidents/spatial-search")
async def spatial_search_incidents(
    body: SpatialSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    geom = body.geometry
    gtype = (geom.get("type") or "").lower()
    coords = geom.get("coordinates")

    if gtype == "point" and body.radius_m and body.radius_m > 0 and coords:
        lon, lat = float(coords[0]), float(coords[1])
        radius = float(body.radius_m)
        search_geom = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        stmt = _base_select().where(
            func.ST_DWithin(
                CrimeEvent.location,
                search_geom,
                radius / 111320.0,
            )
        )
    elif gtype in {"polygon", "multipolygon"}:
        geojson_str = json.dumps(geom)
        search_geom = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geojson_str), 4326)
        stmt = _base_select().where(func.ST_Intersects(CrimeEvent.location, search_geom))
    else:
        raise HTTPException(
            status_code=400,
            detail="Desteklenen geometriler: Polygon, MultiPolygon veya Point+radius_m",
        )

    rows = (await db.execute(stmt)).all()
    fc = rows_to_feature_collection(rows)
    fc["search_geometry"] = geom
    if body.radius_m:
        fc["radius_m"] = body.radius_m
    return fc
