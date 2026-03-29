from __future__ import annotations

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from digest.config import Config


def send_digest(html: str, config: Config) -> None:
    subject = f"Channel Herald — {date.today().strftime('%Y-%m-%d')}"
    msg = _build_message(html, subject, config)
    with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(config.smtp_user, config.smtp_pass)
        smtp.sendmail(config.smtp_user, config.email_to, msg.as_string())


def _build_message(html: str, subject: str, config: Config) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.smtp_user
    msg["To"] = config.email_to
    msg.attach(MIMEText(html, "html"))
    return msg
