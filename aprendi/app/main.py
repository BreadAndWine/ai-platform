"""NAS orchestrator main loop.

Runs a heartbeat (for liveness visibility) and, on every tick, checks
whether it's time to run the scheduled weekly desktop-availability check
(Saturday/Sunday 2am — see scheduler.py and
docs/decisions/0002-compute-orchestration-model.md).

This does not yet run the actual Weekly Learning Brief pipeline (source
fetching, summarization, sending) — see scheduler.py's docstring for what
happens today when the desktop is confirmed ready.
"""

import logging
import os
import time

from scheduler import run_scheduled_check_if_due

LOG_DIR = "/app/logs"
LOG_FILE = os.path.join(LOG_DIR, "orchestrator.log")
HEARTBEAT_INTERVAL_SECONDS = int(
    os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "60")
)

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # visible via `docker logs`
        logging.FileHandler(LOG_FILE),  # persisted on the mounted volume
    ],
)

logger = logging.getLogger("orchestrator")


def main() -> None:
    """Run the orchestrator's main loop: heartbeat + scheduled check."""
    desktop_ip = os.environ.get("DESKTOP_IP")
    desktop_mac = os.environ.get("DESKTOP_MAC")
    lan_broadcast_ip = os.environ.get("LAN_BROADCAST_IP")

    missing = [
        name
        for name, value in [
            ("DESKTOP_IP", desktop_ip),
            ("DESKTOP_MAC", desktop_mac),
            ("LAN_BROADCAST_IP", lan_broadcast_ip),
        ]
        if not value
    ]
    if missing:
        logger.error(
            "Missing required environment variable(s): %s. Scheduled "
            "checks will not run.",
            ", ".join(missing),
        )

    logger.info(
        "Orchestrator started. Heartbeat every %s seconds.",
        HEARTBEAT_INTERVAL_SECONDS,
    )
    while True:
        logger.info("Heartbeat: orchestrator is alive.")
        if not missing:
            run_scheduled_check_if_due(
                desktop_ip, desktop_mac, lan_broadcast_ip
            )
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
