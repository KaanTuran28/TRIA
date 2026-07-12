"""
Ucretsiz Telegram kanal onizleme scraper (API anahtari gerekmez).
https://t.me/s/<kanal> sayfasindan .tgme_widget_message_text icerigini okur.
"""

from __future__ import annotations

import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
)

_MIN_TEXT_LEN = 40
_SKIP_URL_ONLY = re.compile(r"^https?://\S+$", re.I)


def telegram_channels_from_env() -> list[str]:
    from app.modules.crime.sources_config import get_telegram_channels

    return get_telegram_channels()


def _meaningful_post_text(text: str) -> bool:
    """Bos, emoji-only veya yalnizca link iceren gonderileri atla."""
    if len(text) < _MIN_TEXT_LEN:
        return False
    if _SKIP_URL_ONLY.match(text.strip()):
        return False
    letters = re.sub(r"[\s\d\W_]+", "", text, flags=re.UNICODE)
    return len(letters) >= 20


def fetch_telegram_public_channel(channel: str, limit: int = 15) -> list[dict[str, str]]:
    channel = channel.lstrip("@").strip()
    if not channel:
        return []
    url = f"https://t.me/s/{channel}"
    try:
        resp = SESSION.get(url, timeout=25)
        if resp.status_code != 200:
            logger.warning("Telegram HTTP %s: %s", resp.status_code, channel)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        wraps = soup.select(".tgme_widget_message_wrap")
        posts: list[dict[str, str]] = []
        for wrap in wraps[-limit:]:
            text_el = wrap.select_one(".tgme_widget_message_text")
            if not text_el:
                continue
            text = text_el.get_text("\n", strip=True)
            if not _meaningful_post_text(text):
                continue
            link_el = wrap.select_one(".tgme_widget_message_date")
            link = str(link_el["href"]) if link_el and link_el.get("href") else f"https://t.me/s/{channel}"
            posts.append(
                {
                    "title": text.split("\n", 1)[0][:200],
                    "body": text[:4000],
                    "url": link,
                    "source": f"telegram:{channel}",
                }
            )
        return posts
    except Exception as exc:
        logger.warning("Telegram scrape failed %s: %s", channel, exc)
        return []
