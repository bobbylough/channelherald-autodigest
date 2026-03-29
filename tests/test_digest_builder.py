from digest.config import Config
from digest.digest_builder import build_html

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
)


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _summary(
    category: str,
    title: str = "A Title",
    engagers: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": 1,
        "title": title,
        "category": category,
        "summary": "A summary of the article.",
        "read_time": 3,
        "engagers": engagers or [],
    }


def test_ai_story_appears_before_business_story():
    summaries = [_summary("Business"), _summary("AI")]
    html = build_html(summaries, _config())
    ai_pos = html.index("AI")
    business_pos = html.index("Business")
    assert ai_pos < business_pos


def test_engagers_badge_rendered():
    summaries = [_summary("AI", engagers=["software engineer", "entrepreneur"])]
    html = build_html(summaries, _config())
    assert "For: software engineer, entrepreneur" in html


def test_no_external_stylesheets_in_head():
    summaries = [_summary("AI")]
    html = build_html(summaries, _config())
    head_end = html.index("</head>")
    head = html[:head_end]
    assert '<link rel="stylesheet"' not in head
    assert "<style>" not in head


def test_html_has_viewport_meta_tag():
    summaries = [_summary("Technology")]
    html = build_html(summaries, _config())
    assert 'name="viewport"' in html


def test_story_order_ai_business_technology():
    summaries = [
        _summary("Technology", title="Tech Story"),
        _summary("Business", title="Biz Story"),
        _summary("AI", title="AI Story"),
    ]
    html = build_html(summaries, _config())
    ai_pos = html.index("AI Story")
    biz_pos = html.index("Biz Story")
    tech_pos = html.index("Tech Story")
    assert ai_pos < biz_pos < tech_pos


def test_summary_text_in_output():
    summaries = [_summary("AI", title="My Article")]
    html = build_html(summaries, _config())
    assert "A summary of the article." in html
    assert "My Article" in html


def test_non_list_engagers_renders_no_badge():
    summary = {
        "id": 1,
        "title": "T",
        "category": "AI",
        "summary": "S",
        "read_time": 1,
        "engagers": "not-a-list",
    }
    html = build_html([summary], _config())
    assert "For:" not in html
