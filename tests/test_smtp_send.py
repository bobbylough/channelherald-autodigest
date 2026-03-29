from datetime import date
from unittest.mock import MagicMock, patch

from digest.config import Config
from digest.smtp_send import send_digest

_BASE = dict(
    imap_host="imap.example.com",
    imap_port=993,
    imap_user="user@example.com",
    smtp_user="sender@example.com",
    imap_pass="secret",
    smtp_pass="smtppass",
    smtp_host="smtp.example.com",
    smtp_port=587,
    email_to="recipient@example.com",
    llm_provider="groq",
    api_key="key",
    newsletter_senders=["@example.com"],
    preferred_domains=["example.com"],
)

_PATCH = "digest.smtp_send.smtplib.SMTP"


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _make_smtp_mock() -> MagicMock:
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = False
    return mock


def test_starttls_called_before_login():
    smtp_mock = _make_smtp_mock()
    call_order: list[str] = []
    smtp_mock.starttls.side_effect = lambda: call_order.append("starttls")
    smtp_mock.login.side_effect = lambda u, p: call_order.append("login")

    with patch(_PATCH, return_value=smtp_mock):
        send_digest("<html></html>", _config())

    assert call_order.index("starttls") < call_order.index("login")


def test_sendmail_uses_smtp_user_as_sender():
    smtp_mock = _make_smtp_mock()

    with patch(_PATCH, return_value=smtp_mock):
        send_digest("<html></html>", _config())

    args = smtp_mock.sendmail.call_args
    assert args[0][0] == "sender@example.com"


def test_sendmail_uses_email_to_as_recipient():
    smtp_mock = _make_smtp_mock()

    with patch(_PATCH, return_value=smtp_mock):
        send_digest("<html></html>", _config())

    args = smtp_mock.sendmail.call_args
    assert args[0][1] == "recipient@example.com"


def test_subject_contains_todays_date():
    smtp_mock = _make_smtp_mock()
    today = date.today().strftime("%Y-%m-%d")

    with patch(_PATCH, return_value=smtp_mock):
        send_digest("<html></html>", _config())

    raw_message = smtp_mock.sendmail.call_args[0][2]
    assert today in raw_message
