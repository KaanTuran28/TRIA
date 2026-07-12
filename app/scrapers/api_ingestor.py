"""
Yapisal API veri cekicileri — GDELT GKG GeoJSON (Groq bypass fast-track).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests

from app.modules.crime.geolocation import (
    city_from_gdelt_place,
    is_in_turkey,
    resolve_crime_coordinates,
)

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "TRIA-CBS/1.0 (crime-map research)",
        "Accept": "application/json",
    }
)

CATEGORY_ASAYIS = "asayis"
DEFAULT_GKG_URL = "https://api.gdeltproject.org/api/v1/gkg_geojson"
DEFAULT_GKG_QUERY = "geoname:Turkey,ARREST,TAX_FNCACT_POLICE,KILL,TERROR"

_GDELT_BLOCKLIST = (
    "deprem",
    "afet",
    "sel",
    "heyelan",
    "meteoroloji",
    "hava durumu",
    "weather",
    "yangin",
    "yangın",
    "flood",
    "earthquake",
)


def gdelt_severity_from_text(text: str) -> int:
    """Anahtar kelime tabanli AI siddet indeksi (Groq kullanilmaz)."""
    t = (text or "").lower()
    if any(k in t for k in ("murder", "cinayet", "kill", "homicide", "assassination", "oldur")):
        return 9
    if any(k in t for k in ("shooting", "silahli", "armed", "silah", "terror")):
        return 8
    if any(k in t for k in ("arrest", "gozalti", "gözaltı", "custody", "detained")):
        return 7
    if any(k in t for k in ("robbery", "soygun", "gaspa", "hirsizlik", "hırsızlık")):
        return 7
    if any(k in t for k in ("drug", "uyusturucu", "narkotik")):
        return 7
    if any(k in t for k in ("fight", "kavga", "assault", "saldiri")):
        return 6
    if any(k in t for k in ("police", "polis", "jandarma", "operasyon", "operation")):
        return 5
    if any(k in t for k in ("court", "mahkeme", "trial")):
        return 4
    if any(k in t for k in ("crime", "suc", "asayis", "asayiş")):
        return 5
    return 5


def _passes_gdelt_text_filter(text: str) -> bool:
    t = (text or "").lower()
    if any(k in t for k in _GDELT_BLOCKLIST):
        return False
    return True


def _gkg_base_url(config: dict[str, Any]) -> str:
    url = (config.get("url") or DEFAULT_GKG_URL).strip()
    if "/api/v2/geo/geo" in url:
        logger.warning("GDELT v2 geo API 404 veriyor; GKG v1 GeoJSON kullaniliyor")
        return DEFAULT_GKG_URL
    parsed = urlparse(url)
    if parsed.scheme:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return DEFAULT_GKG_URL


def _gkg_queries(config: dict[str, Any]) -> list[str]:
    queries = config.get("queries")
    if isinstance(queries, list) and queries:
        return [str(q).strip() for q in queries if str(q).strip()]
    single = str(config.get("query") or "").strip()
    return [single] if single else [DEFAULT_GKG_QUERY]


def _feature_to_event(feat: dict[str, Any], seen_urls: set[str]) -> dict[str, Any] | None:
    geom = feat.get("geometry") or {}
    if geom.get("type") != "Point":
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    lon, lat = float(coords[0]), float(coords[1])

    props = feat.get("properties") or {}
    place = str(props.get("name") or "").strip()
    themes = str(props.get("mentionedthemes") or props.get("allmentionedthemes") or "")
    article_url = str(props.get("url") or props.get("oneurl") or "").strip()
    context = f"{place} {themes}".strip()
    blob = f"{context} {article_url}".lower()
    if not _passes_gdelt_text_filter(blob):
        return None

    city = city_from_gdelt_place(place)
    geo = resolve_crime_coordinates(
        title=place,
        body=context,
        city_hint=city,
        lat=lat if is_in_turkey(lat, lon) else None,
        lon=lon if is_in_turkey(lat, lon) else None,
    )
    if not geo:
        return None

    title = (place or context)[:500]
    if article_url:
        if article_url in seen_urls:
            return None
        seen_urls.add(article_url)
        source_url = article_url
    else:
        source_url = f"gdelt://event/{hashlib.sha256(context.encode()).hexdigest()[:24]}"

    return {
        "category": CATEGORY_ASAYIS,
        "severity_score": gdelt_severity_from_text(context),
        "description": f"[GDELT Asayis] {context}"[:2000],
        "city": geo["city"],
        "lat": geo["lat"],
        "lon": geo["lon"],
        "confidence": 0.75,
        "title": title,
        "source": "gdelt",
        "source_url": source_url,
    }


def fetch_gdelt(config: dict[str, Any]) -> list[dict[str, Any]]:
    """
    GDELT GKG GeoJSON ceker; her feature icin DB'ye hazir olay dict dondurur.
    Groq LLM atlanir (koordinatlar API'den gelir).
    """
    if not config.get("enabled", True):
        return []

    url = (config.get("url") or "").strip()
    queries = config.get("queries")
    has_queries = isinstance(queries, list) and any(str(q).strip() for q in queries)
    if not url and not has_queries and not str(config.get("query") or "").strip():
        return []

    base = _gkg_base_url(config)
    timespan = int(config.get("timespan_minutes") or 1440)
    maxrows = int(config.get("maxrows") or 250)

    events: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for query in _gkg_queries(config):
        params: dict[str, str | int] = {
            "QUERY": query,
            "TIMESPAN": timespan,
            "MAXROWS": maxrows,
        }
        try:
            resp = SESSION.get(base, params=params, timeout=90)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("GDELT API hatasi (%s): %s", query[:40], exc)
            continue

        features = data.get("features") if isinstance(data, dict) else None
        if not isinstance(features, list):
            continue
        for feat in features:
            if not isinstance(feat, dict):
                continue
            parsed = _feature_to_event(feat, seen_urls)
            if parsed:
                events.append(parsed)

    logger.info("GDELT GKG: %s olay (Turkiye filtresi sonrasi)", len(events))
    return events
