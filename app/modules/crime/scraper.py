import asyncio
import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import cloudscraper
import feedparser
from bs4 import BeautifulSoup
from sqlalchemy import desc, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.modules.crime.dedupe import is_duplicate_title
from app.modules.crime.geometry_utils import crime_point_wkt, utcnow_naive
from app.modules.crime.models import RawNewsArchive
from app.modules.crime.services import parse_raw_news, passes_crime_prefilter
from app.modules.crime.sources_config import (
    get_active_rss_feeds,
    get_gdelt_config,
    get_google_news_rss_feeds,
    get_reddit_rss_feeds,
    get_sources_summary,
    get_telegram_config,
    get_x_rss_bridges,
)
from app.scrapers.api_ingestor import fetch_gdelt
from app.scrapers.telegram_preview import fetch_telegram_public_channel

logger = logging.getLogger(__name__)

SCRAPER_RUN_LOCK = asyncio.Lock()

SCRAPER_METRICS: dict = {
    "feeds_checked": 0,
    "articles_seen": 0,
    "articles_processed": 0,
    "events_created": 0,
    "dedupe_skips": 0,
    "prefilter_skips": 0,
    "llm_rejects": 0,
    "telegram_posts_seen": 0,
    "gdelt_events_seen": 0,
    "gdelt_fast_track_created": 0,
    "last_run_at": None,
    "last_error": None,
}

_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)


def get_scraper_metrics() -> dict:
    return dict(SCRAPER_METRICS)


def is_scraper_running() -> bool:
    return SCRAPER_RUN_LOCK.locked()


def get_pipeline_diagnostics() -> dict:
    summary = get_sources_summary()
    return {
        "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
        "groq_model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "max_article_age_hours": _max_article_age_hours(),
        "max_article_age_filter_active": _max_article_age_hours() > 0,
        "content_similarity_threshold": float(os.getenv("CONTENT_SIMILARITY_THRESHOLD", "0.8")),
        "sources_config_file": summary["config_file"],
        "rss_feed_count": summary["rss_feed_count"],
        "rss_sources": summary["rss_sources"],
        "telegram_channels": summary["telegram_channels"],
        "x_rss_bridges": summary["x_rss_bridges"],
        "google_news_enabled": summary.get("google_news_enabled"),
        "reddit_rss_enabled": summary.get("reddit_rss_enabled"),
        "reddit_feeds": summary.get("reddit_feeds"),
        "gdelt_enabled": summary.get("gdelt_enabled"),
        "gdelt_url": summary.get("gdelt_url"),
    }


async def _insert_crime_event(db: AsyncSession, parsed: dict, source_url: str) -> int | None:
    from app.modules.crime.geolocation import derive_incident_type, normalize_category, resolve_crime_coordinates

    raw_cat = parsed.get("category")
    cat = normalize_category(raw_cat)
    if cat is None:
        # C4I pivotu: afet/yangin artik cop degil, "fire_anomaly" olarak izlenir.
        if derive_incident_type(raw_cat) == "fire_anomaly":
            cat = "afet"
        else:
            return None
    incident_type = derive_incident_type(cat if cat != "afet" else raw_cat)
    geo = resolve_crime_coordinates(
        title=parsed.get("title") or parsed.get("description") or "",
        body=parsed.get("description") or "",
        city_hint=parsed.get("city"),
        lat=parsed.get("lat"),
        lon=parsed.get("lon"),
    )
    if not geo:
        return None
    parsed = {**parsed, "category": cat, "city": geo["city"], "lat": geo["lat"], "lon": geo["lon"]}
    wkt = crime_point_wkt(parsed["lon"], parsed["lat"])
    extra = json.dumps({"source_url": source_url, "confidence": parsed.get("confidence")})
    from app.modules.c4i.dispatch import compute_required_units
    from app.modules.crime.district_lookup import resolve_district

    district = resolve_district(parsed["city"], parsed["lat"], parsed["lon"])

    row = (
        await db.execute(
            text(
                """
                INSERT INTO crime_events
                (category, incident_type, severity_score, description, source, city, district, location,
                 timestamp, source_url, extra_data, required_units, assigned_unit_ids)
                VALUES
                (:category, :incident_type, :severity_score, :description, :source, :city, :district,
                 ST_GeomFromEWKT(:wkt), :timestamp, :source_url, CAST(:extra_data AS jsonb),
                 :required_units, CAST(:assigned_unit_ids AS jsonb))
                RETURNING id
                """
            ),
            {
                "category": parsed["category"],
                "incident_type": incident_type,
                "severity_score": parsed["severity_score"],
                "description": parsed.get("description"),
                "source": parsed.get("source", "osint"),
                "city": parsed.get("city"),
                "district": district,
                "wkt": wkt,
                "timestamp": utcnow_naive(),
                "source_url": source_url,
                "extra_data": extra,
                "required_units": compute_required_units(float(parsed["severity_score"] or 0)),
                "assigned_unit_ids": "[]",
            },
        )
    ).first()
    return int(row[0]) if row else None


def _fetch_rss_feed(feed_url: str):
    """Once cloudscraper ile cek, sonra feedparser — bazi siteler dogrudan parse'i bozar."""
    try:
        resp = _scraper.get(feed_url, timeout=25)
        if resp.status_code == 200 and resp.content:
            parsed = feedparser.parse(resp.content)
            if parsed.entries:
                return parsed
    except Exception as exc:
        logger.debug("RSS cloudscraper %s: %s", feed_url, exc)
    return feedparser.parse(feed_url)


def _fetch_article_text(url: str) -> str:
    try:
        time.sleep(random.uniform(0.4, 1.2))
        resp = _scraper.get(url, timeout=20)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return " ".join(soup.get_text(" ", strip=True).split())[:5000]
    except Exception:
        return ""


def _max_article_age_hours() -> int:
    raw = os.getenv("MAX_ARTICLE_AGE_HOURS", "72").strip()
    if not raw:
        return 72
    try:
        return int(raw)
    except ValueError:
        return 72


def _entry_age_ok(entry) -> bool:
    max_hours = _max_article_age_hours()
    if max_hours <= 0:
        return True
    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if not published:
        return True
    try:
        dt = parsedate_to_datetime(published)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_h <= max_hours
    except Exception:
        return True


async def _load_recent_titles(db: AsyncSession) -> list[str]:
    rows = await db.execute(
        select(RawNewsArchive.title).order_by(desc(RawNewsArchive.id)).limit(3000)
    )
    return [r[0] for r in rows.fetchall() if r[0]]


async def _process_article(
    db: AsyncSession,
    *,
    title: str,
    body: str,
    link: str,
    source_name: str,
    seen_urls: set[str],
    known_titles: list[str],
) -> bool:
    if not link or link in seen_urls:
        SCRAPER_METRICS["dedupe_skips"] += 1
        return False
    if len(body) < 80:
        return False

    if not passes_crime_prefilter(title, body):
        SCRAPER_METRICS["prefilter_skips"] += 1
        return False

    if is_duplicate_title(title, known_titles):
        SCRAPER_METRICS["dedupe_skips"] += 1
        return False

    SCRAPER_METRICS["articles_seen"] += 1
    SCRAPER_METRICS["articles_processed"] += 1
    parsed = parse_raw_news(title, body, source_name)
    if not parsed:
        SCRAPER_METRICS["llm_rejects"] += 1
        return False

    await db.execute(
        pg_insert(RawNewsArchive)
        .values(
            source_url=link,
            title=title[:500],
            content_hash=hashlib.sha256(body.encode()).hexdigest()[:40],
        )
        .on_conflict_do_nothing(index_elements=["source_url"])
    )
    event_id = await _insert_crime_event(db, parsed, link)
    if event_id:
        SCRAPER_METRICS["events_created"] += 1
        seen_urls.add(link)
        known_titles.append(title[:500])
        await db.commit()
        await asyncio.sleep(float(os.getenv("LLM_COOLDOWN_SECONDS", "1") or "1"))
        return True
    await db.commit()
    return False


async def _run_rss_sources(
    db: AsyncSession, feeds: dict[str, str], seen_urls: set[str], known_titles: list[str]
) -> None:
    max_per_feed = int(os.getenv("MAX_ENTRIES_PER_FEED", "10") or "10")
    max_per_feed = max(1, min(max_per_feed, 12))
    for source_name, feed_url in feeds.items():
        SCRAPER_METRICS["feeds_checked"] += 1
        try:
            parsed_feed = await asyncio.to_thread(_fetch_rss_feed, feed_url)
        except Exception as exc:
            logger.warning("Feed okunamadi %s: %s", feed_url, exc)
            continue
        entries = list(parsed_feed.entries or [])
        if not entries:
            logger.warning("RSS bos veya gecersiz: %s (%s)", source_name, feed_url)
            continue
        for entry in entries[:max_per_feed]:
            if not _entry_age_ok(entry):
                continue
            link = (entry.get("link") or "").strip()
            title = (entry.get("title") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            if len(summary) >= 200:
                body = summary
            else:
                body = await asyncio.to_thread(_fetch_article_text, link) or summary
            await _process_article(
                db,
                title=title,
                body=body,
                link=link,
                source_name=source_name,
                seen_urls=seen_urls,
                known_titles=known_titles,
            )


async def _run_gdelt_fast_track(
    db: AsyncSession, seen_urls: set[str], known_titles: list[str]
) -> None:
    """GDELT GeoJSON -> dogrudan PostGIS (Groq LLM atlanir)."""
    cfg = get_gdelt_config()
    if not cfg.get("enabled"):
        return
    events = await asyncio.to_thread(fetch_gdelt, cfg)
    for parsed in events:
        SCRAPER_METRICS["gdelt_events_seen"] += 1
        link = parsed.get("source_url") or ""
        title = parsed.get("title") or parsed.get("description") or "GDELT"
        if link in seen_urls:
            SCRAPER_METRICS["dedupe_skips"] += 1
            continue
        if is_duplicate_title(title, known_titles):
            SCRAPER_METRICS["dedupe_skips"] += 1
            continue
        await db.execute(
            pg_insert(RawNewsArchive)
            .values(
                source_url=link,
                title=title[:500],
                content_hash=hashlib.sha256(title.encode()).hexdigest()[:40],
            )
            .on_conflict_do_nothing(index_elements=["source_url"])
        )
        event_id = await _insert_crime_event(db, parsed, link)
        if event_id:
            SCRAPER_METRICS["gdelt_fast_track_created"] += 1
            SCRAPER_METRICS["events_created"] += 1
            seen_urls.add(link)
            known_titles.append(title[:500])
            await db.commit()


async def _run_telegram_channels(
    db: AsyncSession, seen_urls: set[str], known_titles: list[str]
) -> None:
    tg_cfg = get_telegram_config()
    if not tg_cfg["enabled"]:
        return
    limit = tg_cfg["posts_per_channel"]
    for channel in tg_cfg["channels"]:
        posts = await asyncio.to_thread(fetch_telegram_public_channel, channel, limit)
        await asyncio.sleep(0.4)
        for post in posts:
            SCRAPER_METRICS["telegram_posts_seen"] += 1
            await _process_article(
                db,
                title=post["title"],
                body=post["body"],
                link=post["url"],
                source_name=post["source"],
                seen_urls=seen_urls,
                known_titles=known_titles,
            )


async def run_news_scraper_bot() -> dict:
    if SCRAPER_RUN_LOCK.locked():
        return {"status": "already_running"}
    async with SCRAPER_RUN_LOCK:
        SCRAPER_METRICS["last_error"] = None
        SCRAPER_METRICS["last_run_at"] = datetime.now(timezone.utc).isoformat()
        created_before = SCRAPER_METRICS["events_created"]
        async with AsyncSessionLocal() as db:
            try:
                seen_urls: set[str] = set()
                recent = await db.execute(
                    select(RawNewsArchive.source_url).order_by(desc(RawNewsArchive.id)).limit(5000)
                )
                for (u,) in recent.fetchall():
                    if u:
                        seen_urls.add(u)

                known_titles = await _load_recent_titles(db)

                feeds = get_active_rss_feeds()
                feeds.update(get_google_news_rss_feeds())
                feeds.update(get_reddit_rss_feeds())
                feeds.update(get_x_rss_bridges())

                await _run_gdelt_fast_track(db, seen_urls, known_titles)
                await _run_telegram_channels(db, seen_urls, known_titles)
                await _run_rss_sources(db, feeds, seen_urls, known_titles)
            except Exception as exc:
                logger.exception("Scraper hata")
                SCRAPER_METRICS["last_error"] = str(exc)
                await db.rollback()
        created = SCRAPER_METRICS["events_created"] - created_before
        return {
            "status": "completed",
            "events_created": created,
            "metrics": get_scraper_metrics(),
            "diagnostics": get_pipeline_diagnostics(),
        }
