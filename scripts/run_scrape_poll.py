import sys
import time
import requests

BASE = "http://127.0.0.1:8000"


def main() -> int:
    r = requests.post(f"{BASE}/scrape", timeout=20)
    print("scrape", r.json(), flush=True)

    for i in range(60):
        time.sleep(10)
        m = requests.get(f"{BASE}/scraper/metrics", timeout=120).json()
        running = m.get("running")
        print(
            f"t={i*10}s running={running} created={m.get('events_created')} "
            f"gdelt_ft={m.get('gdelt_fast_track_created')} feeds={m.get('feeds_checked')} "
            f"tg={m.get('telegram_posts_seen')} articles={m.get('articles_processed')} "
            f"err={m.get('last_error')}",
            flush=True,
        )
        if not running:
            break

    stats = requests.get(f"{BASE}/stats", timeout=15).json()
    geo = requests.get(f"{BASE}/geojson", timeout=60).json()
    print("STATS", stats, flush=True)
    print("GEOJSON features", len(geo.get("features", [])), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
