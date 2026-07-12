"""Quick smoke test against running TRIA instance."""
from __future__ import annotations

import json
import sys

import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
TIMEOUT = 20


def get(path: str):
    r = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
    return r.status_code, r


def main() -> int:
    errors = []
    code, r = get("/health")
    print(f"/health -> {code} {r.json()}")
    if code != 200:
        errors.append("health")

    code, r = get("/sources")
    print(f"/sources -> {code}")
    if code == 200:
        s = r.json()
        print(f"  scope={s.get('scope')} gdelt={s.get('gdelt_enabled')} rss={s.get('rss_feed_count')}")
    else:
        errors.append("sources")

    code, r = get("/pipeline/diagnostics")
    print(f"/pipeline/diagnostics -> {code}")
    if code == 200:
        d = r.json()
        print(f"  gdelt_enabled={d.get('gdelt_enabled')}")
    else:
        errors.append("diagnostics")

    code, r = get("/stats")
    print(f"/stats -> {code} {r.json() if code == 200 else r.text[:120]}")
    if code != 200:
        errors.append("stats")

    code, r = get("/geojson")
    n = 0
    if code == 200:
        n = len(r.json().get("features", []))
    print(f"/geojson -> {code} features={n}")
    if code != 200:
        errors.append("geojson")

    code, r = get("/map")
    print(f"/map -> {code} len={len(r.text)}")
    if code != 200 or "leaflet" not in r.text.lower():
        errors.append("map_page")

    code, r = get("/admin")
    print(f"/admin -> {code} len={len(r.text)}")
    if code != 200 or "TRIA" not in r.text:
        errors.append("admin_page")

    r = requests.post(f"{BASE}/scrape", timeout=TIMEOUT)
    code = r.status_code
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:80]
    print(f"POST /scrape -> {code} {body}")

    if errors:
        print("FAIL:", errors)
        return 1
    print("OK: all smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
