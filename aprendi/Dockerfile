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
# shelling out to `ping` is the standard approach, and the Debian package
# retains the capability bit needed to do this without full root).
RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
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
