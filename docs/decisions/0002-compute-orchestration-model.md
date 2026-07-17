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

## Remaining Work

- This test used an ad hoc dev-machine SSH setup, not the NAS. The NAS
  itself will need `wakeonlan` (or equivalent) installed and will need to
  store the desktop's MAC address in its own orchestration config —
  tracked as future work, not yet started.
- The "ask permission if already on" mechanism (see Open Questions above)
  is unrelated to WoL and remains unresolved.
