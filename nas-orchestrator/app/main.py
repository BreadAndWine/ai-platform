"""NAS orchestrator skeleton.

Phase 1 goal: prove the container + scheduling loop works reliably on the
NAS before wiring in real logic (desktop state checks, Wake-on-LAN,
source fetching, etc. — see ADR-0002 and the phase 1 plan for the full
design this will eventually implement).

For now this just logs a heartbeat on an interval, so we can confirm:
- the container starts and stays running
- the memory limit set in docker-compose.yml is respected
- logs are visible both via `docker logs` and the mounted log file
"""

import logging
import os
import time

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
    """Run the orchestrator's main heartbeat loop.

    This is intentionally minimal for the phase 1 skeleton. Future work
    will replace or extend this loop with the actual scheduled job logic
    (desktop state check, Wake-on-LAN, source fetch, etc.).
    """
    logger.info(
        "Orchestrator skeleton started. Heartbeat every %s seconds.",
        HEARTBEAT_INTERVAL_SECONDS,
    )
    while True:
        logger.info("Heartbeat: orchestrator is alive.")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
