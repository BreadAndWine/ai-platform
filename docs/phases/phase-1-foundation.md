# Phase 1: Foundation

## Objectives

- Establish the minimal project documentation structure (ADRs, phase plan).
- [x] Dual-boot Ubuntu 26.04 LTS installed on desktop (SATA SSD, separate
  from Windows' NVMe drive). See ADR-0001 implementation notes.
- [x] Working llama.cpp + Vulkan backend on the RX 9070 XT, verified with
  Qwen2.5-7B-Instruct Q4_K_M: 68.9 tok/s generation, 355.8 tok/s prompt
  processing, confirmed GPU offload via Mesa RADV driver. ROCm was not
  needed — Vulkan performance is strong enough on the first attempt. See
  ADR-0001 implementation notes.
- [x] SSH key-based access from primary dev machine to desktop established
  (ad hoc; not yet documented as a repeatable setup step for NAS-to-desktop
  orchestration — see ADR-0002 open question, still unresolved).
- [x] Wake-on-LAN established and verified end-to-end: desktop shut down
  fully, magic packet sent from another machine on the LAN, desktop
  powered on and booted into Ubuntu automatically. See ADR-0002
  implementation notes.
- [x] "Desktop already on" detection and retry policy decided (ping + SSH
  port check to distinguish Ubuntu/Windows; email + next-day retry, skip
  after 2 consecutive occupied-detections). GRUB configured to show a
  10s menu defaulting to Ubuntu, so unattended WoL boots always land in
  Linux. See ADR-0002.
- [x] Desktop state check + WoL logic implemented in Aprendi
  (`aprendi/app/desktop.py`, `check_desktop.py`) and verified end-to-end
  on the real NAS: shutdown -> WoL -> polling -> correctly detected
  "linux" via SSH port check. Several NAS-specific issues fixed along the
  way (ACLs, capability handling, host networking) — see ADR-0002
  implementation notes.
- [x] Occupied-retry policy from ADR-0002 fully implemented
  (`aprendi/app/job.py`, `state.py`, `run_job_check.py`) and verified in
  all 3 scenarios: happy path (ready, no email), first occupied detection
  (retry-tomorrow email), second consecutive occupied detection
  (skip-this-week email, counter reset).
- [x] Scheduling wired into the heartbeat loop (`aprendi/app/scheduler.py`):
  first attempt Saturday 2am, retry Sunday 2am if occupied. Dedup logic
  (per-week and per-hour) verified working. Found and fixed a real bug
  along the way — Windows Fast Startup (re-enabled by a Windows update)
  was preventing the NIC from being wake-armed at all; disabled, also
  reduces dual-boot filesystem risk. See ADR-0002 implementation notes.
  **The actual brief-generation pipeline still does not exist** — the
  scheduler currently only confirms desktop readiness and logs a
  placeholder.
- [x] Stand up a minimal NAS-side orchestration skeleton, named **Aprendi**
  (see `aprendi/README.md`). Currently a heartbeat-loop container only,
  verified running end-to-end on the actual NAS (built for linux/amd64,
  pushed to ghcr.io, pulled and deployed via UGOS's Docker Compose UI,
  logging on schedule confirmed). Real logic (desktop state check, WoL
  trigger, source fetching/dedup) not yet implemented — this proves the
  container/deployment pipeline works within the NAS's tight memory
  constraints (128MB hard limit).
- [x] Gmail SMTP email delivery working, verified with a real test email
  sent and received via `aprendi/app/mailer.py` /
  `send_test_email.py`. See ADR-0003 implementation notes for the
  `env_file` vs. `${...}` substitution deployment detail.
- [ ] Send one real, end-to-end Weekly Learning Brief email, generated
  from a user-curated source list, using desktop-based inference and
  NAS-based orchestration/delivery. Not started — remaining pieces:
  source fetch/dedup, triggering summarization on the desktop, and
  wiring `job.py` into an actual daily/weekly schedule (rather than
  manual trigger).

## Prerequisites

- [x] User provides an initial seed list of sources (RSS/docs/repos/
  newsletters). See [`docs/sources.md`](../sources.md). Some feed URLs
  still need verification during fetcher implementation.
- User provides/configures an SMTP account (app password) for sending mail.
- Desktop is backed up before dual-boot partitioning (data-loss risk).

## Expected Outcomes

- A documented, working reference architecture for "NAS orchestrates,
  desktop computes on demand," proven with one real use case end-to-end.
- A dual-booted desktop capable of running a 7B-14B class local model at
  usable speed.
- A first working, if narrow, version of the Weekly Learning Brief.

## Risks

- **Dual-boot risk**: partitioning mistakes could affect the existing
  Windows install/games. Mitigate with a full backup before starting.
- **ROCm/RDNA4 maturity risk**: RDNA4 (RX 9070 XT) ROCm support is very
  recent (ROCm 7.2, ~March 2026). Linux support appears more stable than
  Windows, but should be verified directly rather than assumed; Vulkan is
  the fallback backend for llama.cpp if ROCm proves unreliable.
- **NAS resource risk**: 8GB RAM is tight for a Docker-based scheduler plus
  fetch/dedup workloads. Keep NAS-side jobs lightweight; do not run any
  inference there.
- **Scope creep risk**: it is tempting to build autonomous source discovery
  or a nicer pipeline before the basic loop works end-to-end. Resist this;
  v1 is deliberately narrow (see ADR-0003).

## Estimated Effort

At roughly 1 hour/day, phase 1 is estimated at 3-4 weeks, with dual-boot
setup and ROCm/Vulkan verification being the most likely sources of delay.

## Success Criteria

- One real Weekly Learning Brief email is received, generated by a pipeline
  where the NAS handled orchestration/delivery and the desktop handled
  inference, triggered either via Wake-on-LAN or a manual/notification-based
  approval step.
