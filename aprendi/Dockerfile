# Minimal orchestrator skeleton image.
#
# python:3-slim (Debian-based) is used instead of an Alpine variant.
# Alpine's musl libc has caused subtle compatibility issues with some
# Python packages we expect to need later (SSH libraries, HTTP clients for
# RSS fetching, etc.), and this project prioritizes not fighting the base
# image later over shaving a few MB now. Memory usage is controlled via an
# explicit limit in docker-compose.yml instead, given the NAS's tight RAM
# (see ADR-0001 / phase 1 notes).
FROM python:3.13-slim

# iputils-ping provides the `ping` binary used by app/desktop.py to check
# desktop reachability (Python can't easily send raw ICMP without root;
# shelling out to `ping` is the standard approach). libcap2-bin provides
# `setcap`, used below to explicitly grant the ping binary the CAP_NET_RAW
# file capability it needs to open raw sockets as a non-root user — on
# a normal Debian host this capability is usually already present on the
# package's binary, but it does not reliably survive being copied into a
# Docker image layer on this NAS's storage stack, so it's set explicitly
# here instead of relying on it being inherited from the package.
# tzdata provides the IANA timezone database, required for Python's
# zoneinfo module to resolve "Europe/Lisbon" (used by scheduler.py /
# job.py for correct local-time scheduling, including DST handling).
# openssh-client provides the `ssh` binary, used by desktop.py's
# shutdown() to remotely shut down the desktop after a job.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iputils-ping libcap2-bin tzdata openssh-client \
    && setcap cap_net_raw+p /bin/ping \
    && apt-get purge -y --auto-remove libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user. This container currently only does networking
# (ping, WoL, port checks) and log writes, so the practical risk today is
# low, but the container's scope will grow (fetching content, calling out
# to other machines) and least-privilege is cheap to set up now versus
# retrofitting later. See ADR discussion for the reasoning.
RUN useradd --create-home --shell /usr/sbin/nologin aprendi

WORKDIR /app

COPY app/ /app/

RUN chown -R aprendi:aprendi /app

USER aprendi

# No external dependencies yet — the skeleton only uses the standard
# library. Future phases will add a requirements.txt here as real
# functionality (fetching, SSH, email) is implemented.

CMD ["python", "main.py"]
