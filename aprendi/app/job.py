"""The scheduled weekly job's desktop-availability step.

Implements the occupied/retry/skip policy decided in
docs/decisions/0002-compute-orchestration-model.md:

1. Check desktop state (off/linux/windows), waking it if off.
2. If linux (Ubuntu): desktop is ready, proceed with the job.
3. If windows (occupied):
   - First occupied detection: email notifying the job will retry
     tomorrow. Record it.
   - Second consecutive occupied detection: email that the brief is
     being skipped this week, explicitly because of two consecutive
     occupied detections (this also acts as a self-diagnostic signal —
     see ADR-0002's reasoning). Reset the counter.

This module only implements the availability-check step, not the actual
source-fetching/summarization/brief-sending pipeline, which does not
exist yet. run_availability_check() returns True when the desktop is
confirmed ready for a job to proceed; the caller is responsible for
actually running that job.
"""

import datetime
import logging

from desktop import check_and_wake
from mailer import send_email
from state import load_state, save_state

logger = logging.getLogger("aprendi.job")


def _now() -> str:
    return datetime.datetime.now().isoformat()


def run_availability_check(
    ip_address: str, mac_address: str, broadcast_ip: str
) -> bool:
    """Run the desktop availability check and occupied-retry policy.

    Returns True if the desktop is confirmed running Ubuntu and ready for
    a job to proceed now. Returns False in every other case (desktop
    occupied and retry/skip email sent, or desktop unreachable even after
    a wake attempt) — the caller should not proceed with any job in that
    case.
    """
    state = load_state()
    now = _now()

    result = check_and_wake(ip_address, mac_address, broadcast_ip)

    if result == "linux":
        logger.info("Desktop ready (Ubuntu). Proceeding.")
        # Reset the occupied streak on any successful ready-check, so an
        # unrelated occupied attempt in the past doesn't count toward a
        # future streak.
        state["consecutive_occupied_attempts"] = 0
        state["last_attempt_at"] = now
        save_state(state)
        return True

    if result == "windows":
        return _handle_occupied(state, now)

    # "unreachable_after_wake" — desktop did not respond to WoL at all.
    # This is a different failure mode than "occupied" (per ADR-0002,
    # only Windows-vs-Ubuntu detection is the documented occupied case),
    # so it's logged distinctly rather than folded into the same retry
    # counter. Not yet decided how this should be handled long-term —
    # logged for visibility for now.
    logger.warning(
        "Desktop did not respond to Wake-on-LAN. Not treated as "
        "'occupied' — no email sent for this case yet (open item)."
    )
    return False


def _handle_occupied(state: dict, now: str) -> bool:
    """Apply the occupied-retry policy: notify + retry once, then skip
    and notify explicitly on a second consecutive occupied day."""
    previous_streak = state.get("consecutive_occupied_attempts", 0)
    new_streak = previous_streak + 1

    if new_streak >= 2:
        logger.warning(
            "Desktop occupied on 2 consecutive attempts. Skipping this "
            "week's brief."
        )
        send_email(
            subject="Weekly Learning Brief skipped this week",
            body=(
                "The desktop was occupied (running Windows) on two "
                "consecutive scheduled attempts, so this week's brief "
                "is being skipped.\n\n"
                "This is flagged explicitly because two consecutive "
                "occupied-detections overnight is unusual and may "
                "indicate an issue with the desktop rather than normal "
                "use — worth checking if this wasn't expected."
            ),
        )
        state["consecutive_occupied_attempts"] = 0
    else:
        logger.info(
            "Desktop occupied (attempt %s). Will retry tomorrow.",
            new_streak,
        )
        send_email(
            subject="Weekly Learning Brief delayed — desktop in use",
            body=(
                "The scheduled job could not run because the desktop "
                "was in use (running Windows). It will automatically "
                "retry tomorrow at the same scheduled time."
            ),
        )
        state["consecutive_occupied_attempts"] = new_streak

    state["last_attempt_at"] = now
    save_state(state)
    return False
