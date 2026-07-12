"""IBB Acik Veri (CKAN) trafik duyurusu ingestor'u.

Resmi, acik lisansli, olay-duzeyi veri: tip + lat/lon + zaman damgasi.
Yalnizca kaza (traffic_accident) ve arac yangini (fire_anomaly) kayitlari alinir;
bakim-onarim gibi duyurular elenir. Dedupe RawNewsArchive.source_url uzerinden yapilir
(ibb://trafik/<ANNOUNCEMENT_ID> semasi).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import requests
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.modules.crime.geometry_utils import crime_point_wkt
from app.modules.crime.models import RawNewsArchive
from app.modules.crime.sources_config import get_official_api_config

logger = logging.getLogger("tria.ingest.ibb")

SOURCE_NAME = "ibb_acik_veri"
URL_SCHEME = "ibb://trafik/"
REQUEST_TIMEOUT_S = 25

INGEST_METRICS: dict[str, Any] = {
    "last_run_at": None,
    "last_fetched": 0,
    "last_created": 0,
    "last_skipped": 0,
    "last_error": None,
}


def _severity_from_title(title: str) -> float:
    """Kaza siddeti: baslik ipuclarindan (olumlu > yaralanmali > hasarli)."""
    t = (title or "").lower()
    if "ölü" in t or "olu" in t or "can kayb" in t:
        return 8.0
    if "yaralanmal" in t or "yaral" in t:
        return 6.0
    return 4.0


def extract_incident(record: dict[str, Any]) -> dict[str, Any] | None:
    """CKAN kaydini TRIA olayina cevirir; ilgisiz duyuru tiplerinde None."""
    type_desc = str(record.get("ANNOUNCEMENT_TYPE_DESC") or "").lower()
    title = str(record.get("ANNOUNCEMENT_TITLE") or "").strip()

    if "kaza" in type_desc:
        incident_type = "traffic_accident"
        category = "kaza"
        severity = _severity_from_title(title)
    elif "yangın" in type_desc or "yangin" in type_desc:
        incident_type = "fire_anomaly"
        category = "afet"
        severity = 6.0
    else:
        return None  # bakim-onarim, etkinlik vb.

    try:
        lat = float(record["LATITUDE"])
        lon = float(record["LONGITUDE"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (35.0 <= lat <= 43.5 and 25.0 <= lon <= 45.5):
        return None

    ann_id = record.get("ANNOUNCEMENT_ID") or record.get("_id")
    if ann_id is None:
        return None

    ts = None
    raw_ts = record.get("ANNOUNCEMENT_STARTING_DATETIME")
    if raw_ts:
        try:
            ts = datetime.fromisoformat(str(raw_ts))
        except ValueError:
            ts = None

    return {
        "source_url": f"{URL_SCHEME}{ann_id}",
        "category": category,
        "incident_type": incident_type,
        "severity_score": severity,
        "description": title[:500] or type_desc,
        "city": "istanbul",
        "lat": lat,
        "lon": lon,
        "timestamp": ts or datetime.utcnow(),
    }


def _fetch_records(base_url: str, resource_id: str, limit: int) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/3/action/datastore_search"
    resp = requests.get(
        url,
        params={"resource_id": resource_id, "limit": limit, "sort": "_id desc"},
        timeout=REQUEST_TIMEOUT_S,
        headers={"User-Agent": "TRIA-C4I/2.1 (arastirma; acik veri)"},
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("success"):
        raise RuntimeError(f"CKAN success=false: {str(payload)[:200]}")
    return payload.get("result", {}).get("records", []) or []


async def run_ibb_ingest() -> dict[str, Any]:
    """IBB trafik duyurularini ceker ve yeni olaylari crime_events'e yazar."""
    cfg = get_official_api_config("ibb_trafik_duyuru")
    if not cfg or cfg.get("enabled") is not True:
        return {"status": "disabled"}

    base_url = str(cfg.get("base_url") or "https://data.ibb.gov.tr")
    resource_id = str(cfg.get("resource_id") or "")
    limit = int(cfg.get("fetch_limit") or 200)
    if not resource_id:
        return {"status": "error", "detail": "resource_id eksik"}

    INGEST_METRICS["last_run_at"] = datetime.utcnow().isoformat()
    try:
        records = await asyncio.to_thread(_fetch_records, base_url, resource_id, limit)
    except Exception as exc:
        INGEST_METRICS["last_error"] = str(exc)[:300]
        logger.warning("IBB ingest fetch hatasi: %s", exc)
        return {"status": "error", "detail": str(exc)[:300]}

    created = skipped = 0
    async with AsyncSessionLocal() as db:
        for record in records:
            incident = extract_incident(record)
            if not incident:
                skipped += 1
                continue

            # Dedupe: arsivde ayni source_url varsa insert 0 satir etkiler.
            archive_result = await db.execute(
                pg_insert(RawNewsArchive)
                .values(
                    source_url=incident["source_url"],
                    title=incident["description"][:500],
                    content_hash=None,
                )
                .on_conflict_do_nothing(index_elements=["source_url"])
            )
            if not archive_result.rowcount:
                skipped += 1
                continue

            await db.execute(
                text(
                    """
                    INSERT INTO crime_events
                    (category, incident_type, severity_score, description, source, city,
                     location, timestamp, source_url)
                    VALUES
                    (:category, :incident_type, :severity_score, :description, :source, :city,
                     ST_GeomFromEWKT(:wkt), :timestamp, :source_url)
                    """
                ),
                {
                    "category": incident["category"],
                    "incident_type": incident["incident_type"],
                    "severity_score": incident["severity_score"],
                    "description": incident["description"],
                    "source": SOURCE_NAME,
                    "city": incident["city"],
                    "wkt": crime_point_wkt(incident["lon"], incident["lat"]),
                    "timestamp": incident["timestamp"],
                    "source_url": incident["source_url"],
                },
            )
            created += 1
        await db.commit()

    INGEST_METRICS.update(
        {"last_fetched": len(records), "last_created": created, "last_skipped": skipped, "last_error": None}
    )
    logger.info("IBB ingest: %s kayit cekildi, %s olay eklendi, %s atlandi", len(records), created, skipped)
    return {"status": "ok", "fetched": len(records), "events_created": created, "skipped": skipped}
