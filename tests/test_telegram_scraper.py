from app.scrapers.telegram_preview import _meaningful_post_text, fetch_telegram_public_channel


def test_meaningful_post_text_rejects_short_and_link_only():
    assert _meaningful_post_text("https://twitter.com/foo") is False
    assert _meaningful_post_text("kisa") is False
    assert _meaningful_post_text(
        "Ankara'da polis operasyonu: 5 supheli gozaltina alindi. "
        "Olay yerinde arama devam ediyor."
    )


def test_fetch_asayishaber_returns_posts():
    posts = fetch_telegram_public_channel("asayishaber", 3)
    assert isinstance(posts, list)
