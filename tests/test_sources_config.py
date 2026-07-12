from app.modules.crime.sources_config import (
    get_active_rss_feeds,
    get_reddit_rss_feeds,
    get_sources_summary,
    get_telegram_channels,
    google_news_crime_rss_url,
    sources_config_path,
)


def test_sources_config_file_exists():
    path = sources_config_path()
    assert path.is_file(), f"Eksik: {path}"


def test_rss_feeds_loaded():
    feeds = get_active_rss_feeds()
    assert "hurriyet" in feeds
    assert feeds["hurriyet"].startswith("http")


def test_telegram_channels_from_config():
    channels = get_telegram_channels()
    assert len(channels) >= 8
    assert "asayishaber" in channels
    assert "sondakikacc" in channels
    assert "operasyonhaber" in channels


def test_reddit_rss_feeds_loaded():
    feeds = get_reddit_rss_feeds()
    assert len(feeds) >= 1
    assert any("reddit.com" in u for u in feeds.values())


def test_google_news_url_when_enabled():
    url = google_news_crime_rss_url()
    assert url is None or "news.google.com" in url


def test_sources_summary():
    s = get_sources_summary()
    assert s["config_exists"] is True
    assert s["rss_feed_count"] >= 8
    assert s.get("scope") == "asayis_only"
    assert s.get("gdelt_enabled") is True
    assert s.get("reddit_rss_enabled") is True
    assert len(s.get("telegram_channels") or []) >= 8


def test_gdelt_config_loaded():
    from app.modules.crime.sources_config import get_gdelt_config

    cfg = get_gdelt_config()
    assert cfg["enabled"] is True
    assert "gdeltproject.org" in cfg["url"]
    queries = cfg.get("queries") or []
    assert any("geoname:Turkey" in q for q in queries)
