# ADR-0002: Compute Orchestration Model

- **ID**: ADR-0002
- **Date**: 2026-07-16
- **Status**: Accepted (with one open implementation question, see below)
- **Review Date**: 2026-10-16

## Decision

The NAS is the permanent orchestrator; the desktop is a disposable, on-demand
compute resource for inference only.

- The NAS runs the scheduler and all non-inference pipeline steps
  (fetching sources, dedup, storage, email).
- When an inference step is needed, the NAS must get the desktop into a
  state where it can safely run a heavy GPU job:
  - If the desktop is **off**, the NAS wakes it via Wake-on-LAN.
  - If the desktop is **already on**, the NAS must **not** assume it is
    idle. It must ask for permission before starting a heavy inference job,
    because an already-on desktop may be actively in use (e.g. gaming), and
    running inference in the background would degrade that usage and slow
    the job itself.
- Latency is not a constraint for phase 1. Batch/overnight turnaround for
  the weekly brief is acceptable.

## Context

The desktop is a shared-purpose machine (gaming + AI compute), not a
dedicated server. "Powered on" and "available for a heavy background job"
are not the same state. This was identified as a real risk during design:
launching an inference job while the user is gaming would both hurt the
gaming experience and slow down the job.

## Reasoning

Treating "on" as a proxy for "idle" is not a safe assumption on a
shared-purpose machine. The system needs an explicit availability check for
that case. Since latency tolerance is high (batch/overnight is fine), it's
better to delay or ask than to run at a bad time.

## Alternatives Considered

- **Always run regardless of desktop state**: Rejected. Directly conflicts
  with the reason for keeping the desktop as a gaming rig.
- **NAS-only inference**: Rejected, see ADR-0001.
- **Automatically detect idle state (GPU usage, running processes) and
  decide without asking**: Deferred to a later phase. More reliable
  long-term, but more complex to implement correctly, and not needed for a
  weekly, low-frequency job. Revisit once the pipeline exists.

## Trade-offs

- Simpler to implement now (a notification/approval step) at the cost of
  requiring manual interaction sometimes.
- Punts on real idle-detection, which is a better long-term solution but not
  justified yet for a once-a-week job.

## Consequences

- Phase 1 needs a Wake-on-LAN setup between NAS and desktop.
- Phase 1 needs *some* notification mechanism for the "desktop is already on,
  may I run a job?" case. **Open question, not yet decided**: this could be
  a simple email/notification with a manual trigger, a check against a
  known list of game processes/GPU utilization, or something else. To be
  resolved during phase 1 implementation, not before.

## Open Questions

- What is the actual mechanism for "ask permission if desktop is already
  on"? (email + manual step vs. some kind of local notification vs.
  automatic busy-detection). Not blocking phase 1 start, but must be
  resolved before the pipeline can run unattended.
