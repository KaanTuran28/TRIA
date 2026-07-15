"""GeoJSON FeatureCollection yardimcilari."""

from __future__ import annotations

from typing import Any

from app.modules.crime.geolocation import is_in_turkey


def row_to_feature(row: Any) -> dict[str, Any] | None:
    if row.lon is None or row.lat is None:
        return None
    if not is_in_turkey(float(row.lat), float(row.lon)):
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(row.lon), float(row.lat)]},
        "properties": {
            "id": row.id,
            "category": row.category,
            "incident_type": getattr(row, "incident_type", None) or "crime",
            "severity_score": row.severity_score,
            "description": row.description,
            "source": row.source,
            "city": row.city,
            "district": getattr(row, "district", None),
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "source_url": getattr(row, "source_url", None),
            "resolved": getattr(row, "resolved_at", None) is not None,
        },
    }


def rows_to_feature_collection(rows: list[Any]) -> dict[str, Any]:
    features = []
    for row in rows:
        feat = row_to_feature(row)
        if feat:
            features.append(feat)
    return {"type": "FeatureCollection", "features": features, "count": len(features)}
