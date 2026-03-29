from unittest.mock import MagicMock, patch

from digest.config import Config
from digest.digest import run_pipeline

_BASE = dict(
    imap_host="imap.example.com",
    imap_port=993,
    imap_user="user@example.com",
    smtp_user="user@example.com",
    imap_pass="secret",
    smtp_pass="secret",
    smtp_host="smtp.example.com",
    smtp_port=587,
    email_to="recipient@example.com",
    llm_provider="groq",
    api_key="key",
    newsletter_senders=["@example.com"],
    preferred_domains=["example.com"],
    enable_rating=True,
    min_dinner_score=4,
    min_dinner_score_preferred=3,
)


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _article(url: str, title: str, content_depth: int = 2) -> dict[str, object]:
    return {
        "url": url,
        "title": title,
        "body": "body text here",
        "word_count": 200,
        "read_time": 1,
        "content_depth": content_depth,
        "title_only": False,
    }


def _rated(article: dict[str, object], score: int) -> dict[str, object]:
    return {
        **article,
        "dinner_score": score,
        "novelty_score": 2,
        "engagers": [],
        "rating_explanation": "",
    }


def _seen_mock() -> MagicMock:
    mock = MagicMock()
    mock.contains.return_value = False
    return mock


def _summary_for(articles: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {"id": i, "category": "AI", "summary": "s", "read_time": 1}
        for i, _ in enumerate(articles)
    ]


def test_preferred_sender_score3_kept_regular_score3_dropped():
    config = _config()
    emails = [{"body": "", "is_preferred": True}, {"body": "", "is_preferred": False}]
    pref_art = _article("https://pref.com/a", "Preferred Article")
    reg_art = _article("https://reg.com/b", "Regular Article")
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch(
            "digest.digest.extract_links",
            side_effect=[["https://pref.com/a"], ["https://reg.com/b"]],
        ),
        patch("digest.digest.scrape_article", side_effect=[pref_art, reg_art]),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch(
            "digest.digest.rate_article",
            side_effect=[_rated(pref_art, 3), _rated(reg_art, 3)],
        ),
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    urls = [str(a["url"]) for a in captured]
    assert "https://pref.com/a" in urls
    assert "https://reg.com/b" not in urls


def test_jaccard_dedup_keeps_higher_scored_article():
    config = _config()
    emails = [{"body": "", "is_preferred": False}]
    title_a = "Machine Learning in Healthcare"
    title_b = "Machine Learning for Healthcare"
    art_a = _article("https://example.com/a", title_a)
    art_b = _article("https://example.com/b", title_b)
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch(
            "digest.digest.extract_links",
            return_value=["https://example.com/a", "https://example.com/b"],
        ),
        patch("digest.digest.scrape_article", side_effect=[art_a, art_b]),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch(
            "digest.digest.rate_article",
            side_effect=[_rated(art_a, 5), _rated(art_b, 3)],
        ),
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    assert len(captured) == 1
    assert captured[0]["title"] == title_a


def test_content_depth_used_as_tiebreaker():
    config = _config()
    emails = [{"body": "", "is_preferred": False}]
    art_shallow = _article(
        "https://example.com/shallow", "Alpha Article", content_depth=2
    )
    art_deep = _article("https://example.com/deep", "Beta Article", content_depth=4)
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch(
            "digest.digest.extract_links",
            return_value=["https://example.com/shallow", "https://example.com/deep"],
        ),
        patch("digest.digest.scrape_article", side_effect=[art_shallow, art_deep]),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch(
            "digest.digest.rate_article",
            side_effect=[_rated(art_shallow, 4), _rated(art_deep, 4)],
        ),
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    assert captured[0]["title"] == "Beta Article"


def test_seen_urls_skipped():
    config = _config()
    emails = [{"body": "", "is_preferred": False}]
    art = _article("https://example.com/new", "New Article")
    seen = _seen_mock()
    seen.contains.side_effect = lambda url: url == "https://example.com/seen"
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch(
            "digest.digest.extract_links",
            return_value=["https://example.com/seen", "https://example.com/new"],
        ),
        patch("digest.digest.scrape_article", return_value=art),
        patch("digest.digest.SeenUrls", return_value=seen),
        patch("digest.digest.rate_article", return_value=_rated(art, 5)),
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    urls = [str(a["url"]) for a in captured]
    assert "https://example.com/seen" not in urls
    assert "https://example.com/new" in urls


def test_summary_validation_called_when_enabled():
    config = _config(enable_summary_validation=True, summary_min_score=2)
    emails = [{"body": "", "is_preferred": False}]
    art = _article("https://example.com/a", "An Article")
    summary = {"id": 0, "category": "AI", "summary": "Good summary.", "read_time": 1}

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch("digest.digest.extract_links", return_value=["https://example.com/a"]),
        patch("digest.digest.scrape_article", return_value=art),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch("digest.digest.rate_article", return_value=_rated(art, 5)),
        patch("digest.digest.summarize_batch", return_value=[summary]),
        patch("digest.digest.validate_summary", return_value=summary) as mock_validate,
    ):
        run_pipeline(config)

    mock_validate.assert_called_once()


def test_rating_disabled_skips_rate_and_filter():
    config = _config(enable_rating=False)
    emails = [{"body": "", "is_preferred": False}]
    art = _article("https://example.com/a", "Some Article")
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch("digest.digest.extract_links", return_value=["https://example.com/a"]),
        patch("digest.digest.scrape_article", return_value=art),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch("digest.digest.rate_article") as mock_rate,
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    mock_rate.assert_not_called()
    assert len(captured) == 1


def test_empty_title_articles_not_duplicated():
    config = _config(enable_rating=False)
    emails = [{"body": "", "is_preferred": False}]
    art_a = _article("https://example.com/a", "")
    art_b = _article("https://example.com/b", "")
    captured: list[dict[str, object]] = []

    def fake_summarize(
        articles: list[dict[str, object]], cfg: Config
    ) -> list[dict[str, object]]:
        captured.extend(articles)
        return _summary_for(articles)

    with (
        patch("digest.digest.fetch_emails", return_value=emails),
        patch(
            "digest.digest.extract_links",
            return_value=["https://example.com/a", "https://example.com/b"],
        ),
        patch("digest.digest.scrape_article", side_effect=[art_a, art_b]),
        patch("digest.digest.SeenUrls", return_value=_seen_mock()),
        patch("digest.digest.summarize_batch", side_effect=fake_summarize),
    ):
        run_pipeline(config)

    # Jaccard(∅, ∅) = 0.0 — not > 0.5, so both are kept (not duplicates)
    assert len(captured) == 2
