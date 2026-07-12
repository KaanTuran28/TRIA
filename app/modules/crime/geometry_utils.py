from datetime import datetime, timezone


def crime_point_wkt(lon: float, lat: float) -> str:
    return f"SRID=4326;POINT({lon} {lat})"


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
