"""Manual, on-demand desktop state check + wake.

Run inside the container via:
    docker exec aprendi python check_desktop.py

This is intentionally separate from the main.py heartbeat loop — this
phase is only about proving the state-detection and WoL logic works
correctly, not about running it automatically yet. Wiring it into a
schedule (and adding the occupied/retry/email policy from ADR-0002) is
later work.

Configuration is read from environment variables (set in
docker-compose.yml) rather than hardcoded, so the desktop's network
details aren't duplicated across files.
"""

import logging
import os
import sys

from desktop import check_and_wake

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("aprendi.check_desktop")


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

    logger.info("Checking desktop state (ip=%s)...", ip_address)
    final_state = check_and_wake(ip_address, mac_address, broadcast_ip)

    if final_state == "linux":
        logger.info("RESULT: Desktop is ONLINE running Ubuntu. Ready for jobs.")
    elif final_state == "windows":
        logger.info("RESULT: Desktop is ONLINE but running Windows (occupied).")
    else:
        logger.warning("RESULT: Desktop did not come online after WoL attempt.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
