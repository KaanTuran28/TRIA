"""Kaynak bazli veri cekme diagnostigi."""
from __future__ import annotations

import asyncio
import json
import sys
import time

import feedparser
import requests

sys.path.insert(0, ".")

from app.modules.crime.sources_config import (
    get_active_rss_feeds,
    get_gdelt_config,
    get_google_news_rss_feeds,
    get_reddit_rss_feeds,
    get_telegram_config,
    reload_sources_config,
)
from app.scrapers.api_ingestor import fetch_gdelt
from app.scrapers.telegram_preview import fetch_telegram_public_channel


def test_rss(name: str, url: str) -> dict:
    try:
        from app.modules.crime.scraper import _fetch_rss_feed

        d = _fetch_rss_feed(url)
        n = len(d.entries)
        err = d.bozo and str(getattr(d, "bozo_exception", ""))[:80] or None
        return {"ok": n > 0, "entries": n, "error": err}
    except Exception as e:
        return {"ok": False, "entries": 0, "error": str(e)[:120]}


def main() -> int:
    reload_sources_config()
    report: dict = {"sources": {}, "errors": []}

    print("=== GDELT ===")
    t0 = time.time()
    gdelt = fetch_gdelt(get_gdelt_config())
    report["sources"]["gdelt"] = {"ok": len(gdelt) > 0, "events": len(gdelt), "sec": round(time.time() - t0, 1)}
    print(report["sources"]["gdelt"])

    print("\n=== RSS ===")
    rss = get_active_rss_feeds()
    rss_ok = 0
    for name, url in rss.items():
        r = test_rss(name, url)
        report["sources"][f"rss:{name}"] = r
        if r["ok"]:
            rss_ok += 1
        else:
            report["errors"].append(f"rss:{name}: {r.get('error')}")
        print(f"  {name}: {r}")
    report["rss_summary"] = {"total": len(rss), "ok": rss_ok}

    print("\n=== Google News RSS ===")
    gn = get_google_news_rss_feeds()
    for name, url in gn.items():
        r = test_rss(name, url)
        report["sources"][f"gn:{name}"] = r
        print(f"  {name}: {r}")

    print("\n=== Reddit RSS ===")
    rd = get_reddit_rss_feeds()
    for name, url in rd.items():
        r = test_rss(name, url)
        report["sources"][f"reddit:{name}"] = r
        print(f"  {name}: {r}")

    print("\n=== Telegram ===")
    tg = get_telegram_config()
    tg_ok = 0
    for ch in tg["channels"]:
        posts = fetch_telegram_public_channel(ch, 5)
        ok = len(posts) > 0
        if ok:
            tg_ok += 1
        report["sources"][f"tg:{ch}"] = {"ok": ok, "posts": len(posts)}
        print(f"  {ch}: posts={len(posts)}")
    report["telegram_summary"] = {"total": len(tg["channels"]), "ok": tg_ok}

    print("\n=== API health ===")
    try:
        h = requests.get("http://127.0.0.1:8000/health", timeout=5).json()
        report["api"] = h
        print(h)
    except Exception as e:
        report["api"] = {"ok": False, "error": str(e)}
        print("API down:", e)

    out = "ingestion_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out}")
    fail = len(report["errors"])
    return 0 if report["sources"].get("gdelt", {}).get("ok") or rss_ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
