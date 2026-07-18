"""Email sending via Gmail SMTP.

Per ADR-0003: uses an existing Gmail account over SMTP with an App
Password (requires 2-Step Verification on the account), not a
self-hosted mail server. Credentials are read from environment
variables only — never hardcoded (see .env.example and the project's
security steering).
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger("aprendi.mailer")

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587  # STARTTLS


def send_email(subject: str, body: str) -> bool:
    """Send a plain-text email via Gmail SMTP.

    Reads GMAIL_ADDRESS, GMAIL_APP_PASSWORD, and BRIEF_RECIPIENT_EMAIL
    from the environment. Returns True on success, False on failure
    (failures are logged, not raised, so a notification failure doesn't
    crash whatever caller triggered it — the caller decides how to react
    to a False return).
    """
    sender = os.environ.get("GMAIL_ADDRESS")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient = os.environ.get("BRIEF_RECIPIENT_EMAIL")

    missing = [
        name
        for name, value in [
            ("GMAIL_ADDRESS", sender),
            ("GMAIL_APP_PASSWORD", app_password),
            ("BRIEF_RECIPIENT_EMAIL", recipient),
        ]
        if not value
    ]
    if missing:
        logger.error(
            "Cannot send email, missing environment variable(s): %s",
            ", ".join(missing),
        )
        return False

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient

    try:
        with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], message.as_string())
        logger.info("Email sent: subject=%r to=%s", subject, recipient)
        return True
    except smtplib.SMTPException as exc:
        # Deliberately not logging the exception's raw args in case any
        # SMTP error response ever echoes back credential-adjacent detail
        # (unlikely with Gmail, but avoid taking the risk). The exception
        # type name alone is enough to diagnose auth vs. connection issues.
        logger.error("Failed to send email (%s).", type(exc).__name__)
        return False
