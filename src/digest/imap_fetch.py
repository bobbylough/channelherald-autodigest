from __future__ import annotations

import email as email_module
import email.message
import imaplib
from datetime import date, timedelta
from email.utils import parseaddr

from digest.config import Config


def fetch_emails(config: Config) -> list[dict[str, object]]:
    since = (
        date.today() - timedelta(days=config.email_lookback_days)
    ).strftime("%d-%b-%Y")
    results: list[dict[str, object]] = []
    with imaplib.IMAP4_SSL(config.imap_host, config.imap_port) as imap:
        imap.login(config.imap_user, config.imap_pass)
        imap.select("INBOX")
        for sender in config.newsletter_senders:
            _, data = imap.search(None, f'(FROM "{sender}" SINCE {since})')
            for email_id in (data[0] or b"").split():
                body, from_addr = _fetch_email(imap, email_id)
                is_pref = any(
                    _matches(from_addr, p) for p in config.preferred_senders
                )
                results.append({"body": body, "is_preferred": is_pref})
    return results


def _fetch_email(
    imap: imaplib.IMAP4_SSL, email_id: bytes
) -> tuple[str, str]:
    _, msg_data = imap.fetch(email_id.decode(), "(RFC822)")
    raw: bytes = msg_data[0][1]  # type: ignore[index,assignment]
    msg = email_module.message_from_bytes(raw)
    _, from_addr = parseaddr(msg.get("From", ""))
    return _extract_html(msg), from_addr.lower()


def _extract_html(msg: email.message.Message) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                return payload.decode("utf-8", errors="replace")
    return ""


def _matches(address: str, pattern: str) -> bool:
    pattern = pattern.lower()
    if pattern.startswith("@"):
        return address.endswith(pattern)
    return address == pattern
