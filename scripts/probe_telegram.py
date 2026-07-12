"""Probe public Telegram channels via t.me/s preview."""
from __future__ import annotations

import json
import sys

from app.scrapers.telegram_preview import fetch_telegram_public_channel

CANDIDATES = [
    "asayishaber",
    "operasyonhaber",
    "conflict_tr",
    "sondakikacc",
    "ajans_muhbir",
    "ensonhaber",
    "haberler",
    "haberpaylasim",
    "sondakika",
    "anadoluajansi",
    "polisgundem",
    "muhbirhaber",
    "internethaber",
    "haberint",
    "gundemchannel",
    "turkishnews",
    "breakingturkey",
    "sondakikaturkiye",
    "gundemturkiye",
    "siyasetgundem",
    "haber365tr",
    "turkiyegazetesi",
    "yurtgazetesi",
    "asayisberkemaltr",
]


def main() -> None:
    out = []
    for ch in CANDIDATES:
        posts = fetch_telegram_public_channel(ch, 5)
        out.append(
            {
                "channel": ch,
                "count": len(posts),
                "sample": posts[0]["title"][:80] if posts else None,
            }
        )
    path = sys.argv[1] if len(sys.argv) > 1 else "telegram_probe.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    working = [x for x in out if x["count"] > 0]
    print(f"ok={len(working)}/{len(out)} -> {path}")


if __name__ == "__main__":
    main()
