"""Ilce (district) cozumleme — point-in-polygon, turkey-ilce.geojson kaynagini kullanir.

Onceden crime_events.district yalnizca manuel ihbarda (dispatcher elle yazinca) doluyordu.
Bu modul OSINT/IBB kaynakli olaylara da otomatik ilce atamasi yapar — coklu-birim ve ilce
bazli analitik (breakdown/districts) her kaynaktan gelen veriyle calisabilsin diye.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape

logger = logging.getLogger(__name__)

_GEOJSON_PATH = Path(__file__).resolve().parents[3] / "frontend" / "static" / "geo" / "turkey-ilce.geojson"


@lru_cache(maxsize=1)
def _district_index() -> dict[str, list[tuple[str, object]]]:
    """il -> [(ilce_adi, shapely_polygon), ...] — process basina bir kez yuklenir."""
    index: dict[str, list[tuple[str, object]]] = {}
    try:
        with open(_GEOJSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.warning("turkey-ilce.geojson yuklenemedi (%s) — district cozumleme devre disi", exc)
        return index
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        il, ilce = props.get("il"), props.get("ilce")
        if not il or not ilce or not feat.get("geometry"):
            continue
        try:
            poly = shape(feat["geometry"])
        except Exception:
            continue
        index.setdefault(il, []).append((ilce, poly))
    return index


def _normalize_district_name(name: str) -> str:
    """OSM'de "<il> merkez" formatinda gelen adlari kanonik "Merkez" haline getirir.

    Sevk/tohum verisi ("dispatcher elle Merkez yazar") ile OSM kaynagi arasindaki
    isimlendirme farkini tek noktada cozer (frontend'deki ayri normalizasyon yerine).
    """
    return "Merkez" if name.strip().lower().endswith("merkez") else name.strip()


def list_districts(city: str | None) -> list[str]:
    """Bir ilin ilce adlarini (normalize + tekillestirilmis, alfabetik) dondurur."""
    if not city:
        return []
    districts = _district_index().get(city.strip().lower())
    if not districts:
        return []
    names = {_normalize_district_name(name) for name, _poly in districts}
    return sorted(names, key=lambda s: s.lower())


def resolve_district(city: str | None, lat: float | None, lon: float | None) -> str | None:
    """Sehir + koordinata gore ilce adi (point-in-polygon); bulunamazsa None.

    Bir ilin ilce sayisi kucuk oldugu icin (2-40 arasi) tam spatial index'e gerek yok —
    dogrusal tarama yeterince hizli (ingestion sirasinda tek seferlik cagri).
    """
    if not city or lat is None or lon is None:
        return None
    districts = _district_index().get(city.strip().lower())
    if not districts:
        return None
    point = Point(float(lon), float(lat))
    for name, poly in districts:
        if poly.intersects(point):
            return name
    return None
