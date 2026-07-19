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
    # ISO year-week string, e.g. "2026-W29". Set when a week's job either
    # proceeds successfully or is explicitly skipped (2 consecutive
    # occupied attempts) — i.e. when the week is "resolved" and the
    # scheduler should not attempt it again until next week.
    "resolved_for_week": None,
    # "<date>-<hour>" string, e.g. "2026-07-18-02". Set every time the
    # scheduler runs a check attempt (regardless of outcome), so the
    # heartbeat loop (firing every ~60s) doesn't re-trigger the check
    # repeatedly within the same scheduled hour.
    "last_checked_slot": None,
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
