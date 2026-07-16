# ai-platform

A personal, local-first AI ecosystem, built incrementally over multiple
years. Optimized for long-term learning, maintainability, and architectural
quality over short-term progress.

See `prompt.md` for the operating charter this project is run under.

## Documentation

- [`docs/decisions/`](docs/decisions/) — Architecture Decision Records (ADRs).
  Start with [ADR-0001](docs/decisions/0001-hardware-topology-and-constraints.md)
  for the hardware/compute baseline.
- [`docs/phases/`](docs/phases/) — Phase plans. Current phase:
  [Phase 1: Foundation](docs/phases/phase-1-foundation.md).

## Status

Phase 1 (Foundation) — not yet started. See the phase plan for objectives,
prerequisites, and success criteria.

## Hardware

- **NAS**: UGREEN DXP2800 (Intel N100, 8GB RAM, UGOS + Docker). Always-on
  orchestration and storage.
- **Desktop**: Ryzen 5600X + AMD RX 9070 XT. On-demand GPU inference
  (Windows gaming rig, to be dual-booted with Linux).
- **Laptop**: MacBook Air M4.

No cloud APIs, no cloud spend. See ADR-0001 for the reasoning.

## First Application

Weekly Learning Brief: a locally-generated, emailed digest curating AI/LLM,
software engineering, AWS, and related learning material from a
user-curated source list. See ADR-0003 for v1 scope.
