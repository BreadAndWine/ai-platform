"""Persistent state for the scheduled job's occupied-retry policy.

State is stored as JSON on the same mounted log volume already used by
main.py (permissions already verified working on the NAS — see ADR-0002
implementation notes), so it survives container restarts. Without
persistence, a restart between "day 1 occupied" and "day 2 occupied"
would silently reset the retry count, and the skip-after-2-consecutive-
attempts policy from ADR-0002 would never trigger.
"""

import json
import logging
import os

logger = logging.getLogger("aprendi.state")

STATE_FILE = os.path.join(
    os.environ.get("STATE_DIR", "/app/logs"), "job_state.json"
)

DEFAULT_STATE = {
    # ISO 8601 datetime string, e.g. "2026-07-18T02:00:14.123456"
    "last_attempt_at": None,
    "consecutive_occupied_attempts": 0,
}


def load_state() -> dict:
    """Load job state from disk, falling back to defaults if missing
    or unreadable."""
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        return {**DEFAULT_STATE, **data}
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(
            "Failed to read state file (%s); using defaults.",
            type(exc).__name__,
        )
        return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    """Persist job state to disk."""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError as exc:
        logger.error("Failed to write state file (%s).", type(exc).__name__)
