"""Desktop state detection and Wake-on-LAN for the gaming rig / GPU host.

Implements the state-detection and wake logic decided in
docs/decisions/0002-compute-orchestration-model.md:

- Ping the desktop. No response -> off -> send a WoL magic packet.
- If ping succeeds, check whether SSH (port 22) is reachable.
  - Reachable -> Ubuntu is running (only Ubuntu runs an SSH server here).
  - Unreachable -> Windows is running (the only other expected state,
    given the dual-boot setup) -> desktop is "occupied".

This module only detects state and can send a wake packet — it does not
yet trigger any inference job or send email notifications. Those are
later steps once this logic is proven.
"""

import logging
import socket
import subprocess
import time

logger = logging.getLogger("aprendi.desktop")

# Standard port for Wake-on-LAN magic packets. Some implementations use
# port 7 instead; 9 is the more common default and what we verified
# working during manual WoL testing.
WOL_PORT = 9

SSH_PORT = 22


def send_wol(mac_address: str, broadcast_ip: str) -> None:
    """Send a Wake-on-LAN magic packet to wake the target machine.

    A magic packet is a UDP packet whose payload is 6 bytes of 0xFF
    followed by the target's 6-byte MAC address repeated 16 times. Any
    device on the LAN receives it (since it's sent to the broadcast
    address), but only the NIC matching the MAC address (in its
    low-power listening state) acts on it.

    Args:
        mac_address: Target MAC address, e.g. "d8:5e:d3:05:33:de".
        broadcast_ip: The LAN's broadcast address, e.g. "192.168.1.255".
    """
    mac_bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    if len(mac_bytes) != 6:
        raise ValueError(f"Invalid MAC address: {mac_address}")

    magic_packet = b"\xff" * 6 + mac_bytes * 16

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast_ip, WOL_PORT))

    logger.info("Sent Wake-on-LAN magic packet to %s", mac_address)


def is_host_reachable(ip_address: str, timeout_seconds: int = 2) -> bool:
    """Check whether a host responds to a single ICMP ping.

    Shells out to the system `ping` command rather than using a raw
    socket, since sending real ICMP packets from Python normally
    requires root privileges. `ping` is a normal, unprivileged command
    that already has the necessary capability set on most Linux
    systems (including inside this container, once iputils-ping is
    installed — see Dockerfile).
    """
    result = subprocess.run(
        ["ping", "-c", "1", "-W", str(timeout_seconds), ip_address],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def is_port_open(
    ip_address: str, port: int, timeout_seconds: int = 3
) -> bool:
    """Check whether a TCP port is open on the given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            sock.connect((ip_address, port))
            return True
        except OSError:
            return False


def determine_state(ip_address: str) -> str:
    """Determine the desktop's current state without sending a wake packet.

    Returns one of: "off", "linux", "windows".
    """
    if not is_host_reachable(ip_address):
        return "off"
    if is_port_open(ip_address, SSH_PORT):
        return "linux"
    return "windows"


def check_and_wake(
    ip_address: str,
    mac_address: str,
    broadcast_ip: str,
    wake_wait_seconds: int = 90,
    poll_interval_seconds: int = 5,
) -> str:
    """Check desktop state; if off, wake it and wait for it to come up.

    This does not attempt any occupied-retry/email logic (see ADR-0002 for
    that policy) — it only determines and returns the final state after a
    wake attempt, for now via logging only.

    Returns one of: "linux", "windows", "unreachable_after_wake".
    """
    state = determine_state(ip_address)
    logger.info("Initial desktop state: %s", state)

    if state != "off":
        return state

    send_wol(mac_address, broadcast_ip)

    waited = 0
    while waited < wake_wait_seconds:
        time.sleep(poll_interval_seconds)
        waited += poll_interval_seconds
        state = determine_state(ip_address)
        logger.info(
            "Post-wake check at +%ss: state=%s", waited, state
        )
        if state != "off":
            return state

    logger.warning(
        "Desktop did not respond within %ss after WoL packet.",
        wake_wait_seconds,
    )
    return "unreachable_after_wake"
