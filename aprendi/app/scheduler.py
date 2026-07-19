"""Weekly schedule check, driven by the main.py heartbeat loop.

Per the user's decision: first attempt Saturday at 2am, retry Sunday 2am
if occupied (per ADR-0002's policy), giving a full weekend of buffer
before the brief would be sent Monday. The actual brief-sending pipeline
does not exist yet — see run_scheduled_check_if_due()'s docstring.

This module does not run its own timer; it's checked on every heartbeat
tick in main.py. Precision is therefore only as good as the heartbeat
interval (default 60s) — acceptable for a weekly job.
"""

import datetime
import logging

from job import is_week_already_resolved, run_availability_check
from state import load_state, save_state

logger = logging.getLogger("aprendi.scheduler")

# Saturday=5, Sunday=6 in Python's date.weekday() (Monday=0).
SCHEDULED_WEEKDAYS = {5, 6}
SCHEDULED_HOUR = 2


def _current_slot() -> str:
    """A per-hour identifier, e.g. '2026-07-18-02', used to ensure the
    heartbeat loop only triggers one check per scheduled hour, not once
    per heartbeat tick within that hour."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d-%H")


def _is_scheduled_now() -> bool:
    now = datetime.datetime.now()
    return now.weekday() in SCHEDULED_WEEKDAYS and now.hour == SCHEDULED_HOUR


def run_scheduled_check_if_due(
    ip_address: str, mac_address: str, broadcast_ip: str
) -> None:
    """Run the availability check if it's the scheduled time and this
    week isn't already resolved.

    NOTE: this only runs the desktop-availability check + occupied-retry
    policy (see job.py / ADR-0002). It does not yet fetch sources,
    summarize, or send an actual Weekly Learning Brief — that pipeline
    does not exist yet. When the desktop is confirmed ready, this
    currently only logs that fact; wiring in the real pipeline is future
    work.
    """
    if not _is_scheduled_now():
        return

    if is_week_already_resolved():
        return

    slot = _current_slot()
    state = load_state()
    if state.get("last_checked_slot") == slot:
        # Already ran a check during this specific hour; avoid
        # re-triggering on every subsequent heartbeat tick within it.
        return

    state["last_checked_slot"] = slot
    save_state(state)

    logger.info("Scheduled check triggered (slot=%s).", slot)
    ready = run_availability_check(ip_address, mac_address, broadcast_ip)

    if ready:
        logger.info(
            "Desktop ready. [PLACEHOLDER] This is where source "
            "fetching, summarization, and brief sending would run — "
            "not yet implemented."
        )
