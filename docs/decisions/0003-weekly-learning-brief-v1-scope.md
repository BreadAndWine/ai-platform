# ADR-0003: Weekly Learning Brief v1 Scope

- **ID**: ADR-0003
- **Date**: 2026-07-16
- **Status**: Accepted
- **Review Date**: 2026-10-16

## Decision

The first application, the Weekly Learning Brief, is scoped down for v1 as
follows:

- **Sources**: a small, user-curated seed list (RSS feeds, docs sites,
  GitHub repos/orgs, newsletters), provided manually by the user. No
  autonomous source discovery in v1.
- **Pipeline**: NAS fetches and deduplicates source content; the
  summarization/curation step runs as an LLM inference job on the desktop
  (per ADR-0001/ADR-0002).
- **Delivery**: output is sent via email, using an existing SMTP account
  (e.g. an app password on a personal mail provider). No self-hosted mail
  server in v1.
- **Audience**: single user (the project owner) only.
- **Latency**: batch/overnight is acceptable; no real-time requirement.

## Context

The user has no existing source list and no strong opinion on autonomous
discovery yet. Self-hosting email was raised as an option but explicitly
deprioritized.

## Reasoning

Autonomous source discovery with no curated seed list is a much harder
problem than summarizing a known-good set of sources, and doing it badly
produces confidently-wrong recommendations, which actively works against
the "avoid low quality/no educational value content" principle in the
project charter. Starting with a human-curated list lets the team validate
summarization/curation quality first, and defer discovery until that's
proven.

Self-hosting mail has low learning value relative to its effort and
deliverability risk (spam filtering, DNS/SPF/DKIM/DMARC setup, IP
reputation), and it is not on the user's stated list of learning priorities
(AI/LLMs, AWS, Networking). Using an existing SMTP account is the pragmatic
choice for v1.

## Alternatives Considered

- **Autonomous source discovery from day one**: Rejected for v1, deferred to
  a later phase once curation/summarization quality is proven against a
  known-good source list.
- **Self-hosted mail**: Deferred. Revisit only if there's a specific
  learning goal that justifies it later.

## Trade-offs

- Faster path to a working, trustworthy v1 at the cost of manual source
  curation effort from the user up front.

## Consequences

- User needs to supply an initial source list before phase 1 can be
  completed end-to-end.
- User needs to supply/configure an SMTP account (app password) for sending
  the brief.
