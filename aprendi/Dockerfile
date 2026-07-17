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

WORKDIR /app

COPY app/ /app/

# No external dependencies yet — the skeleton only uses the standard
# library. Future phases will add a requirements.txt here as real
# functionality (fetching, SSH, email) is implemented.

CMD ["python", "main.py"]
