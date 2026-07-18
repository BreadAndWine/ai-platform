"""Manual, on-demand test of the full availability-check + retry policy.

Run inside the container via the container console:
    python run_job_check.py

Unlike check_desktop.py (which only detects/wakes and logs), this one
also applies the ADR-0002 occupied-retry policy and sends real emails
when the desktop is occupied — use deliberately, not as a casual repeat
test, since running it twice in a row while the desktop is on Windows
will trigger the "skip this week" email on the second run.

To reset the retry counter for testing, delete the state file:
    rm /app/logs/job_state.json
"""

import logging
import os
import sys

from job import run_availability_check

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("aprendi.run_job_check")


def main() -> int:
    ip_address = os.environ.get("DESKTOP_IP")
    mac_address = os.environ.get("DESKTOP_MAC")
    broadcast_ip = os.environ.get("LAN_BROADCAST_IP")

    missing = [
        name
        for name, value in [
            ("DESKTOP_IP", ip_address),
            ("DESKTOP_MAC", mac_address),
            ("LAN_BROADCAST_IP", broadcast_ip),
        ]
        if not value
    ]
    if missing:
        logger.error(
            "Missing required environment variable(s): %s",
            ", ".join(missing),
        )
        return 1

    ready = run_availability_check(ip_address, mac_address, broadcast_ip)
    logger.info("run_availability_check returned: %s", ready)
    return 0


if __name__ == "__main__":
    sys.exit(main())
