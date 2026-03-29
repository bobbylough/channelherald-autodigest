from digest.config import Config
from digest.link_extractor import extract_links

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
    preferred_domains=["preferred.com"],
    max_articles_per_email=3,
)


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _email(body: str, is_preferred: bool = False) -> dict[str, object]:
    return {"body": body, "is_preferred": is_preferred}


def test_preferred_domain_link_ranked_first_despite_late_position():
    html = (
        '<a href="https://regular1.com/a">Alpha article title here</a>'
        '<a href="https://regular2.com/b">Beta article title here</a>'
        '<a href="https://regular3.com/c">Gamma article title here</a>'
        '<a href="https://regular4.com/d">Delta article title here</a>'
        '<a href="https://preferred.com/e">Epsilon preferred article</a>'
    )
    config = _config()
    result = extract_links(_email(html), config)

    assert result[0] == "https://preferred.com/e"


def test_utm_params_stripped_from_returned_url():
    html = (
        '<a href="https://example.com/article'
        '?utm_source=newsletter&utm_medium=email&id=42">Read more</a>'
    )
    config = _config()
    result = extract_links(_email(html), config)

    assert len(result) == 1
    assert "utm_source" not in result[0]
    assert "utm_medium" not in result[0]
    assert "id=42" in result[0]


def test_only_http_https_urls_returned():
    html = (
        '<a href="mailto:someone@example.com">Email</a>'
        '<a href="ftp://files.example.com/doc">FTP</a>'
        '<a href="https://example.com/article">Article</a>'
    )
    config = _config()
    result = extract_links(_email(html), config)

    assert result == ["https://example.com/article"]


def test_cap_applied_for_regular_email():
    links = "".join(
        f'<a href="https://site{i}.com/article">Title number {i} here</a>'
        for i in range(6)
    )
    config = _config(max_articles_per_email=3)
    result = extract_links(_email(links, is_preferred=False), config)

    assert len(result) == 3


def test_cap_doubled_for_preferred_email():
    links = "".join(
        f'<a href="https://site{i}.com/article">Title number {i} here</a>'
        for i in range(8)
    )
    config = _config(max_articles_per_email=3)
    result = extract_links(_email(links, is_preferred=True), config)

    assert len(result) == 6
