"""
Tum scraper kaynaklari config/sources.json dosyasindan yuklenir.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_SOURCES_FILE = _PROJECT_ROOT / "config" / "sources.json"

_cache: dict[str, Any] | None = None
_cache_mtime: float | None = None


def sources_config_path() -> Path:
    raw = os.getenv("SOURCES_CONFIG_PATH", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else _PROJECT_ROOT / p
    return _DEFAULT_SOURCES_FILE


def _load_raw() -> dict[str, Any]:
    global _cache, _cache_mtime
    path = sources_config_path()
    if not path.is_file():
        logger.warning("Kaynak dosyasi bulunamadi: %s — varsayilanlar kullanilacak", path)
        return {}
    mtime = path.stat().st_mtime
    if _cache is not None and _cache_mtime == mtime:
        return _cache
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Gecersiz kaynak dosyasi (dict bekleniyor): {path}")
    _cache = data
    _cache_mtime = mtime
    logger.info("Kaynak dosyasi yuklendi: %s", path)
    return data


def reload_sources_config() -> None:
    global _cache, _cache_mtime
    _cache = None
    _cache_mtime = None
    _load_raw()


def _parse_rss_entry(name: str, entry: Any) -> tuple[str, str] | None:
    if isinstance(entry, str):
        url = entry.strip()
        if url:
            return name, url
        return None
    if isinstance(entry, dict):
        if entry.get("enabled") is False:
            return None
        url = (entry.get("url") or "").strip()
        if url:
            return name, url
    return None


def get_rss_feeds() -> dict[str, str]:
    data = _load_raw()
    rss = data.get("rss") or {}
    if not isinstance(rss, dict):
        return {}
    out: dict[str, str] = {}
    for name, entry in rss.items():
        if name.startswith("_"):
            continue
        parsed = _parse_rss_entry(str(name), entry)
        if parsed:
            out[parsed[0]] = parsed[1]
    return out


def get_active_rss_feeds() -> dict[str, str]:
    data = _load_raw()
    all_feeds = get_rss_feeds()
    if data.get("use_priority_rss_only") is True:
        priority = data.get("priority_rss") or []
        if isinstance(priority, list):
            return {k: all_feeds[k] for k in priority if k in all_feeds}
    env_priority = os.getenv("USE_PRIORITY_FEEDS_ONLY", "").strip().lower()
    if env_priority in {"1", "true", "yes"}:
        priority = data.get("priority_rss") or []
        if isinstance(priority, list):
            return {k: all_feeds[k] for k in priority if k in all_feeds}
    return all_feeds


def get_telegram_config() -> dict[str, Any]:
    data = _load_raw()
    tg = data.get("telegram") or {}
    if not isinstance(tg, dict):
        tg = {}
    enabled = tg.get("enabled", True)
    channels = tg.get("channels") or ["anadoluajansi", "ensonhaber"]
    if not isinstance(channels, list):
        channels = ["anadoluajansi", "ensonhaber"]
    posts = int(tg.get("posts_per_channel") or os.getenv("TELEGRAM_POSTS_PER_CHANNEL", "12") or 12)
    return {
        "enabled": bool(enabled),
        "channels": [str(c).strip().lstrip("@") for c in channels if str(c).strip()],
        "posts_per_channel": max(1, posts),
    }


def get_telegram_channels() -> list[str]:
    cfg = get_telegram_config()
    if not cfg["enabled"]:
        return []
    return cfg["channels"]


def get_google_news_config() -> dict[str, Any]:
    data = _load_raw()
    gn = data.get("google_news") or {}
    if not isinstance(gn, dict):
        gn = {}
    enabled = gn.get("enabled", True)
    queries = gn.get("queries")
    if isinstance(queries, list) and queries:
        return {"enabled": bool(enabled), "queries": queries}
    query = gn.get("query") or (
        "Turkiye (cinayet OR operasyon OR polis OR jandarma OR silah) when:1d"
    )
    return {"enabled": bool(enabled), "queries": [{"name": "default", "query": str(query)}]}


def get_google_news_rss_feeds() -> dict[str, str]:
    """Birden fazla Google News sorgusu -> feed adi: url."""
    cfg = get_google_news_config()
    if not cfg["enabled"]:
        return {}
    if os.getenv("GOOGLE_NEWS_CRIME_RSS", "").strip().lower() in {"0", "false", "no"}:
        return {}
    out: dict[str, str] = {}
    for item in cfg.get("queries") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "google_news").strip()
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        out[f"google_news_{name}"] = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + "&hl=tr&gl=TR&ceid=TR:tr"
        )
    return out


def google_news_crime_rss_url() -> str | None:
    feeds = get_google_news_rss_feeds()
    if not feeds:
        return None
    return next(iter(feeds.values()))


def get_gdelt_config() -> dict[str, Any]:
    data = _load_raw()
    apis = data.get("apis") or {}
    if not isinstance(apis, dict):
        return {"enabled": False}
    gdelt = apis.get("gdelt_crime_turkey") or {}
    if not isinstance(gdelt, dict):
        return {"enabled": False}
    queries = gdelt.get("queries")
    if isinstance(queries, list):
        qlist = [str(q).strip() for q in queries if str(q).strip()]
    else:
        qlist = []
    single = str(gdelt.get("query") or "").strip()
    if single and not qlist:
        qlist = [single]
    return {
        "enabled": gdelt.get("enabled", True) is not False,
        "url": str(gdelt.get("url") or "").strip(),
        "queries": qlist,
        "timespan_minutes": int(gdelt.get("timespan_minutes") or 1440),
        "maxrows": int(gdelt.get("maxrows") or 250),
    }


def get_reddit_rss_feeds() -> dict[str, str]:
    """Reddit public search RSS — ucretsiz, anahtarsiz."""
    data = _load_raw()
    block = data.get("reddit_rss") or {}
    if not isinstance(block, dict) or block.get("enabled") is False:
        return {}
    if os.getenv("REDDIT_RSS_ENABLED", "").strip().lower() in {"0", "false", "no"}:
        return {}
    feeds = block.get("feeds") or []
    if not isinstance(feeds, list):
        return {}
    out: dict[str, str] = {}
    for item in feeds:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "reddit").strip()
        url = str(item.get("url") or "").strip()
        if url.startswith("http"):
            out[f"reddit_{name}" if not name.startswith("reddit") else name] = url
    return out


def get_x_rss_bridges() -> dict[str, str]:
    data = _load_raw()
    bridges = data.get("x_rss_bridges") or {}
    if not isinstance(bridges, dict):
        return {}
    out: dict[str, str] = {}
    for name, entry in bridges.items():
        if name.startswith("_"):
            continue
        if isinstance(entry, str) and entry.strip():
            out[str(name)] = entry.strip()
        elif isinstance(entry, dict) and entry.get("enabled") is not False:
            url = (entry.get("url") or "").strip()
            if url:
                out[str(name)] = url
    return out


def get_official_api_config(name: str) -> dict[str, Any]:
    """Resmi acik veri kaynagi ayarlari (sources.json > official_apis)."""
    data = _load_raw()
    apis = data.get("official_apis") or {}
    entry = apis.get(name) or {}
    return entry if isinstance(entry, dict) else {}


def get_sources_summary() -> dict[str, Any]:
    path = sources_config_path()
    feeds = get_active_rss_feeds()
    feeds.update(get_google_news_rss_feeds())
    feeds.update(get_reddit_rss_feeds())
    feeds.update(get_x_rss_bridges())
    tg = get_telegram_config()
    gdelt = get_gdelt_config()
    return {
        "config_file": str(path),
        "config_exists": path.is_file(),
        "scope": "asayis_only",
        "rss_feed_count": len(feeds),
        "rss_sources": list(feeds.keys()),
        "telegram_enabled": tg["enabled"],
        "telegram_channels": tg["channels"] if tg["enabled"] else [],
        "google_news_enabled": get_google_news_config()["enabled"],
        "google_news_query_count": len(get_google_news_rss_feeds()),
        "reddit_rss_enabled": bool(get_reddit_rss_feeds()),
        "reddit_feeds": list(get_reddit_rss_feeds().keys()),
        "gdelt_enabled": gdelt["enabled"],
        "gdelt_url": gdelt.get("url"),
        "x_rss_bridges": list(get_x_rss_bridges().keys()),
    }
