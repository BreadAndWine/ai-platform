"""Manual, on-demand test of the mailer.

Run inside the container via the container console:
    python send_test_email.py

Sends a single test email using the configured Gmail credentials, to
confirm the SMTP setup works before it's relied on by any real logic
(e.g. the ADR-0002 occupied/retry notifications).
"""

import logging
import sys

from mailer import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def main() -> int:
    success = send_email(
        subject="Aprendi test email",
        body=(
            "This is a test email from Aprendi, confirming Gmail SMTP "
            "delivery is working correctly."
        ),
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
