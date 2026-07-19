# ADR-0002: Compute Orchestration Model

- **ID**: ADR-0002
- **Date**: 2026-07-16 (core decision resolved 2026-07-17)
- **Status**: Accepted
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

## Decision: Desktop State Detection and Retry Policy

Resolved 2026-07-17. This closes the primary open question from this ADR.

### State detection

The orchestrator (eventually the NAS) determines desktop state without
needing any custom agent on the desktop itself, using only network-level
checks:

1. **Ping the desktop.** No response → desktop is off → send a
   Wake-on-LAN magic packet (see Implementation Notes above), wait for
   boot, then re-check.
2. **If ping succeeds, check SSH (port 22) reachability.**
   - **SSH reachable → Ubuntu is running.** Only Ubuntu runs an SSH
     server (Windows does not, and won't be configured to for this
     purpose); this is sufficient to distinguish the two OSes without any
     additional signaling. Proceed with the inference job.
   - **SSH unreachable but ping succeeds → Windows is running** (the only
     other expected state given the dual-boot setup). Do not attempt the
     job. Fall through to the retry policy below.

This deliberately avoids needing any in-Windows agent, notification
service, or OpenSSH-on-Windows setup that was considered earlier in this
ADR's discussion — it was dropped in favor of this simpler, purely
network-level check.

### Boot default and manual override

- GRUB (installed on the SATA SSD, independent of Windows' own
  bootloader) is configured with `GRUB_TIMEOUT_STYLE=menu` and
  `GRUB_TIMEOUT=10`, defaulting to Ubuntu (`GRUB_DEFAULT=0`, first menu
  entry).
- This means: an unattended Wake-on-LAN boot always lands in Ubuntu with
  no extra logic needed, since nothing is pressed during the 10-second
  window.
- To game, the user manually selects "Windows Boot Manager" from the GRUB
  menu during that window. This was chosen over a motherboard-level
  one-time boot menu because GRUB already lists Windows as a detected
  entry (via `os-prober`) and requires no BIOS interaction.
- This does not reintroduce the original Windows-update/GRUB-clobbering
  risk from ADR-0001: GRUB itself lives entirely on the SATA SSD's ESP.
  Windows updates can only affect files on Windows' own ESP (the NVMe
  drive), which could at worst break the "Windows Boot Manager" menu
  entry's target, not GRUB itself. Recoverable, and does not reproduce the
  "Linux becomes unreachable" failure mode.

### Retry policy when Windows is detected (desktop occupied)

1. On first detection that Windows is running (desktop occupied): send an
   email notifying that the scheduled job could not run because the
   desktop was in use, and that it will retry the next day.
2. Reschedule the job for the next day (same time-of-day target, e.g.
   2am).
3. If Windows is detected occupied on the retry (i.e. two consecutive
   failures): send an email stating the weekly brief is being skipped this
   week, explicitly because the desktop was occupied on two consecutive
   attempts. This is a deliberate signal, not just a silent skip — two
   consecutive occupied-detections in the middle of the night is unlikely
   to be normal gaming behavior, and is called out explicitly so the user
   can notice if something is actually wrong with the desktop (e.g. it's
   stuck in Windows for an unrelated reason) rather than assume it's just
   being used.
4. No further automatic retries beyond the second attempt for that week's
   job. This bounds the retry behavior and avoids indefinite silent
   rescheduling.

## Remaining Open Questions

- None remaining for the core "how do we know desktop state, and what do
  we do about it" question — resolved above.
- Implementation of this logic as an actual script/scheduled job is
  deferred until the NAS-side orchestration skeleton exists (not yet
  built as of this writing). This ADR captures the decision; it is not
  yet wired into working automation.

## Implementation Notes (Wake-on-LAN)

Verified 2026-07-17.

Wake-on-LAN was set up and tested end-to-end between a dev machine (Mac)
and the desktop, standing in for the eventual NAS-to-desktop trigger.

- **Desktop-side (Ubuntu) configuration**, three layers had to align:
  1. **BIOS/UEFI**: "Wake on LAN" setting confirmed enabled (checked
     manually, not scriptable/remote).
  2. **NIC driver (live state)**: checked and set via `ethtool`:
     ```
     sudo ethtool enp4s0          # check current Wake-on state
     sudo ethtool -s enp4s0 wol g # enable magic-packet wake
     ```
     `enp4s0` is this machine's NIC name (Ubuntu predictable naming); the
     supported modes reported were `pumbg`, and `g` (magic packet) is the
     one WoL depends on. This setting alone does **not** persist across
     reboots — the NIC driver resets it, which is why the NetworkManager
     step below was also needed.
  3. **NetworkManager (persistent)**: the live `ethtool` change resets on
     reboot unless also set at the connection-profile level:
     ```
     sudo nmcli connection modify netplan-enp4s0 \
       802-3-ethernet.wake-on-lan magic
     ```
     `netplan-enp4s0` is the specific NetworkManager connection profile
     name for this interface (find via `nmcli device show <iface>` and
     look for `GENERAL.CONNECTION`). This is what makes the setting survive
     reboots, since NetworkManager reapplies it whenever the interface
     comes up.
- **Desktop MAC address**: `d8:5e:d3:05:33:de` (interface `enp4s0`). Magic
  packets target the MAC address, not an IP, since the machine has no
  running OS/IP stack while powered off.
- **Sudo scoping**: rather than granting broad passwordless sudo (a real
  security downgrade on a network-reachable machine), specific commands
  were whitelisted in `/etc/sudoers.d/marcelo-wol` via `visudo`:
  ```
  marcelo ALL=(ALL) NOPASSWD: /usr/sbin/ethtool
  marcelo ALL=(ALL) NOPASSWD: /usr/bin/nmcli
  marcelo ALL=(ALL) NOPASSWD: /usr/sbin/shutdown
  ```
  `shutdown` was added because the desktop will need to power itself off
  after future automated jobs (per this ADR's decision), not just for this
  test.
- **Sender-side test** (from the dev machine, standing in for the NAS):
  ```
  brew install wakeonlan
  wakeonlan -i 192.168.1.255 d8:5e:d3:05:33:de
  ```
  `-i 192.168.1.255` is the LAN's broadcast address; the magic packet is
  sent to all devices on the subnet, and only the NIC matching the target
  MAC address (in its low-power listening state) acts on it.
- **Result**: desktop was shut down fully (`sudo shutdown -h now`),
  confirmed offline (100% ping loss), magic packet sent from the dev
  machine, desktop powered on and became reachable via ping and SSH within
  ~30-45 seconds. Full end-to-end success, not just configuration without
  a real test.

## Implementation Notes (Aprendi: NAS-Side Desktop Check + WoL)

Verified 2026-07-18. This replaces the earlier "ad hoc dev machine" setup
with the real NAS-side implementation, in `aprendi/app/desktop.py` and
`aprendi/app/check_desktop.py` (manual trigger only for now; not yet wired
into a schedule).

`check_and_wake()` implements exactly the logic decided above: ping-based
reachability, WoL send if off, SSH port (22) check to distinguish
Ubuntu/Windows once reachable. Verified end-to-end on the actual NAS
(not a dev machine): desktop shut down, script run from inside the
`aprendi` container's console, WoL sent, desktop detected `off` for ~40s
then `linux` at 45s, script printed "Desktop is ONLINE running Ubuntu.
Ready for jobs."

### Issues hit and fixed along the way

Several environment-specific problems had to be resolved before this
worked — all fixed in `aprendi/Dockerfile` and `docker-compose.yml`, and
worth remembering since they'll matter for any future container on this
NAS, not just this one:

1. **Docker Desktop for Mac cannot be used to test this logic.** Even with
   `--network host`, containers run inside Docker Desktop's Linux VM on
   Mac, which does not share the Mac's real network interfaces the way
   native Linux Docker does. WoL sends appeared to succeed but
   ping/port-checks back to LAN devices did not work reliably. Bare
   Python (no container) on the Mac worked correctly and was used to
   validate the logic itself before deploying to the NAS.
2. **Docker's default bridge network isolates containers from the
   physical LAN.** WoL requires broadcasting a UDP packet onto the real
   network; this does not reliably escape the default bridge. Fixed with
   `network_mode: host` in `docker-compose.yml` — matching the pattern
   already used by this NAS's other LAN-dependent containers (e.g. Home
   Assistant).
3. **NAS storage uses POSIX ACLs (visible as a `+` suffix on `ls -la`
   permission bits), which can override plain Unix permission bits.**
   The container's non-root user (UID 1000) could not write to the
   mounted log volume even after `chown`, because ACL entries scoped to
   named NAS users/groups were still in effect. Fixed with
   `setfacl -R -b` to strip ACLs from the specific mounted folder,
   falling back to plain Unix permissions, before `chown`/`chmod`.
4. **`cap_add: NET_RAW` at the container level was not sufficient on its
   own** for a non-root process to open raw ICMP sockets via `ping`. The
   `CAP_NET_RAW` file capability normally embedded in the Debian
   `iputils-ping` binary does not reliably survive being copied into a
   Docker image layer on this NAS's storage stack. Fixed by explicitly
   running `setcap cap_net_raw+p /bin/ping` during the image build (while
   still root, before switching to the non-root `aprendi` user), in
   addition to `cap_add: NET_RAW` in compose.
5. **Wake time is ~35-45 seconds in practice** (including the 10s GRUB
   menu delay from this ADR's boot-default decision). The default
   `wake_wait_seconds` was increased from an initial 45s to 90s for
   comfortable margin.

### Non-root container design

The `aprendi` container runs as a dedicated non-root user (UID/GID 1000),
not root, per least-privilege — see Dockerfile comments. This is a
deliberate choice given the container's scope will grow (source fetching,
eventually triggering jobs on the desktop), even though today's
networking-only workload has low inherent risk.

## Implementation Notes (Occupied-Retry Policy)

Verified 2026-07-18. `aprendi/app/job.py` (`run_availability_check()`)
composes `desktop.py` + `mailer.py` + a new `state.py` module into the
full policy decided above:

- Persistent state (`job_state.json`, on the same mounted log volume) so
  the consecutive-occupied counter survives container restarts between
  attempts — without this, a restart between two occupied days would
  silently reset the counter and the skip-after-2 policy would never
  trigger.
- Full ISO datetime (not just date) is recorded for each attempt, for
  better diagnostics and to support future scheduling sanity checks.

All three scenarios were tested manually via `run_job_check.py` (a new
manual trigger, distinct from `check_desktop.py` which only detects/wakes
without applying the retry policy) and confirmed working:

1. **Happy path**: desktop off/Ubuntu → detected/woken, confirmed ready,
   no email sent, counter reset.
2. **First occupied detection**: desktop on Windows → "delayed, retrying
   tomorrow" email sent, counter set to 1.
3. **Second consecutive occupied detection**: desktop still on Windows →
   "skipped this week" email sent instead, counter reset to 0.

**Known simplification, deliberate**: the policy counts *consecutive
occupied detections*, not real elapsed time between attempts — running
the check twice in a row (as in manual testing) triggers the "skip" case
immediately, rather than requiring a real day to pass. This is fine in
practice since the eventual production schedule will only run once daily,
but is a known gap if this logic is ever invoked more than once per day
for a reason other than testing.

## Implementation Notes (Scheduling)

Verified 2026-07-19. `aprendi/app/scheduler.py`, driven by the existing
`main.py` heartbeat loop (no separate cron process — see this ADR's
earlier reasoning for preferring the simpler option), checks on every
heartbeat tick whether it's the scheduled time and triggers
`run_availability_check()` if so.

**Schedule**: first attempt Saturday 2am, retry Sunday 2am if occupied
(per the existing occupied-retry policy), giving a full weekend of buffer
before a brief would be sent Monday — the user's choice, to maximize
recovery time before the week starts.

**Dedup logic**, both verified working:
- `resolved_for_week` (ISO year-week) prevents re-attempting a week that
  already succeeded or was explicitly skipped.
- `last_checked_slot` (date+hour) prevents the heartbeat loop (ticking
  every ~60s) from re-triggering the check repeatedly within the same
  scheduled hour.

Tested by temporarily overriding `SCHEDULED_HOUR` to the current hour
(since waiting for an actual Saturday/Sunday 2am wasn't practical) and
calling `run_scheduled_check_if_due()` directly from the container
console. First call correctly woke the desktop and detected it ready;
second call within the same hour correctly did nothing (silent, by
design — the only path with no log statement).

### Bug found and fixed along the way: Windows Fast Startup broke WoL

During this testing, a real regression was found: after a Windows update,
the desktop stopped waking via WoL entirely (timed out after 90s). Linux
side (`ethtool`) still correctly showed `Wake-on: g` — ruling out anything
this project had configured. The actual cause was **Windows Fast
Startup**, confirmed via `powercfg /devicequery wake_armed` showing only
mouse/keyboard devices, not the Ethernet NIC — meaning Windows had not
armed the NIC to wake the system at all, regardless of what Device
Manager's (misleadingly greyed-out) checkboxes appeared to show.

Fast Startup makes shutdown behave like a partial hibernation rather than
a true power-off, which can prevent network adapters from being armed for
wake. It's also a known cause of dual-boot filesystem issues (NTFS can be
left in a "not fully unmounted" state, causing mount problems or rarer
corruption when accessed from Linux) — a second, independent reason to
disable it in a dual-boot setup regardless of the WoL issue.

**Fix**: disabled Fast Startup via Control Panel → Power Options →
"Choose what the power buttons do" → "Change settings that are currently
unavailable" → uncheck "Turn on fast startup (recommended)". After a full
shutdown (not restart) with this disabled, the NIC appeared correctly in
`wake_armed`, and WoL worked again.

**Takeaway for future debugging**: `powercfg /devicequery wake_armed` is
the authoritative way to check Windows-side wake-arming status — Device
Manager's Power Management tab checkboxes can appear checked/greyed-out
in a way that does not reliably reflect actual armed state.

## Implementation Notes (Automatic Shutdown + Timezone)

Verified 2026-07-19.

**Timezone**: `scheduler.py` and `job.py` use Python's `zoneinfo` with an
explicit `Europe/Lisbon` timezone (not the container's default UTC),
correctly handling DST (confirmed `+01:00` / WEST offset at test time).
`tzdata` added to the Dockerfile to provide the IANA timezone database
`zoneinfo` depends on.

**Automatic shutdown**: since no real brief-generation pipeline exists
yet, leaving the desktop running indefinitely after a successful wake
would defeat the point of treating it as an on-demand resource (ADR-0001)
and require the user to remember to shut it down manually every time.
`desktop.shutdown()` now SSHes into the desktop (as a dedicated Aprendi
keypair, not the user's personal key) and runs `sudo shutdown -h now`,
relying on the passwordless-shutdown sudoers rule already configured
during original WoL setup. Called immediately after a successful
readiness check in `scheduler.py`; this will move to "after the real job
completes" once a pipeline exists, rather than immediately after
readiness.

Setup required a dedicated SSH keypair, generated on the NAS and
authorized on the desktop's `~/.ssh/authorized_keys`, mounted read-only
into the container. Two permission issues were hit and fixed along the
way, both consistent with earlier ACL/permission findings on this NAS:

1. SSH refuses to use a private key with overly-open permissions
   ("UNPROTECTED PRIVATE KEY FILE" warning) — fixed with `chmod 600` on
   the key file.
2. The container's non-root user (UID 1000) could not read the key even
   after that, since it was owned by the NAS shell user, not UID 1000 —
   fixed with `chown 1000:1000` on the key file specifically (no ACL
   stripping needed this time, unlike the log volume earlier).

End-to-end verified: manually triggered a scheduled check, desktop woke
and was confirmed ready, then powered itself off automatically — no
manual shutdown needed.

## Remaining Work

- The scheduler, occupied-retry policy, and automatic post-check shutdown
  are all implemented and verified. What's still missing is the actual
  Weekly Learning Brief pipeline itself (source fetch/dedup, triggering
  summarization on the desktop, assembling and sending the real brief) —
  currently the desktop just shuts back down right after being confirmed
  ready, with no job run in between.
- No handling yet for the `unreachable_after_wake` case (desktop doesn't
  respond to WoL at all) — currently logged only, not emailed, and not
  folded into the occupied-retry counter. Open item.
- The GHCR-based build/push/redeploy loop (dev machine builds for
  linux/amd64, pushes to ghcr.io, NAS redeploys) works but requires a full
  compose redeploy — not just a container restart — for code, environment
  variable, or capability changes to take effect. Worth remembering for
  future iteration speed.
