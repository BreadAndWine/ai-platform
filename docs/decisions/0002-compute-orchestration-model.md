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

## Remaining Work

- This logic is implemented but only manually triggered
  (`docker exec` / container console → `python check_desktop.py`). It is
  not yet wired into a schedule, and the occupied/retry/email policy
  decided above is not yet implemented in code.
- The GHCR-based build/push/redeploy loop (dev machine builds for
  linux/amd64, pushes to ghcr.io, NAS redeploys) works but requires a full
  compose redeploy — not just a container restart — for code, environment
  variable, or capability changes to take effect. Worth remembering for
  future iteration speed.
