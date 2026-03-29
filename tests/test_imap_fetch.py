import email.mime.multipart
import email.mime.text
from unittest.mock import MagicMock, patch

from digest.config import Config
from digest.imap_fetch import fetch_emails

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
    preferred_domains=["example.com"],
)


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _raw_email(from_addr: str, html: str) -> bytes:
    msg = email.mime.multipart.MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["Subject"] = "Test"
    msg.attach(email.mime.text.MIMEText(html, "html"))
    return msg.as_bytes()


def _make_imap(search_results: list[bytes], fetch_results: list[bytes]) -> MagicMock:
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.search.side_effect = [("OK", [ids]) for ids in search_results]
    mock.fetch.side_effect = [
        ("OK", [(b"1 (RFC822 {0})", raw)]) for raw in fetch_results
    ]
    return mock


def test_result_dicts_have_body_and_is_preferred_keys():
    config = _config(
        newsletter_senders=["@example.com"],
        preferred_senders=["@example.com"],
    )
    raw = _raw_email("news@example.com", "<html><body>hello</body></html>")
    imap_mock = _make_imap([b"1"], [raw])

    with patch("digest.imap_fetch.imaplib.IMAP4_SSL", return_value=imap_mock):
        results = fetch_emails(config)

    assert len(results) == 1
    assert "body" in results[0]
    assert "is_preferred" in results[0]


def test_preferred_sender_sets_is_preferred_true():
    config = _config(
        newsletter_senders=["@example.com", "@other.com"],
        preferred_senders=["@example.com"],
    )
    raw_pref = _raw_email("news@example.com", "<html><body>pref</body></html>")
    raw_reg = _raw_email("news@other.com", "<html><body>regular</body></html>")
    imap_mock = _make_imap([b"1", b"2"], [raw_pref, raw_reg])

    with patch("digest.imap_fetch.imaplib.IMAP4_SSL", return_value=imap_mock):
        results = fetch_emails(config)

    assert len(results) == 2
    pref = next(r for r in results if "pref" in str(r["body"]))
    reg = next(r for r in results if "regular" in str(r["body"]))
    assert pref["is_preferred"] is True
    assert reg["is_preferred"] is False


def test_no_emails_returns_empty_list():
    config = _config(
        newsletter_senders=["@example.com"],
        preferred_senders=[],
    )
    imap_mock = _make_imap([b""], [])

    with patch("digest.imap_fetch.imaplib.IMAP4_SSL", return_value=imap_mock):
        results = fetch_emails(config)

    assert results == []


def test_plain_text_only_email_returns_empty_body():
    import email.mime.text as _t

    config = _config(
        newsletter_senders=["@example.com"],
        preferred_senders=[],
    )
    msg = _t.MIMEText("plain text only", "plain")
    msg["From"] = "news@example.com"
    imap_mock = _make_imap([b"1"], [msg.as_bytes()])

    with patch("digest.imap_fetch.imaplib.IMAP4_SSL", return_value=imap_mock):
        results = fetch_emails(config)

    assert results[0]["body"] == ""


def test_exact_email_address_preferred_match():
    config = _config(
        newsletter_senders=["news@example.com"],
        preferred_senders=["news@example.com"],
    )
    raw = _raw_email("news@example.com", "<html><body>hi</body></html>")
    imap_mock = _make_imap([b"1"], [raw])

    with patch("digest.imap_fetch.imaplib.IMAP4_SSL", return_value=imap_mock):
        results = fetch_emails(config)

    assert results[0]["is_preferred"] is True
