---
inclusion: always
---

# Project Git Workflow (overrides global git steering for this repo)

This is a solo, personal, long-term project. It is not tracked in Jira and
does not use feature branches for now.

- **MUST NOT** ask for a Jira ID before committing. This project has no
  Jira tracking.
- **MUST** commit directly to `main`. No feature branches required at this
  stage.
- **MUST** commit whenever a decision-level milestone is reached — e.g. a
  new or updated ADR, a phase plan created or completed, or any other
  change to `docs/decisions/` or `docs/phases/`. Documentation is the
  source of truth (see `prompt.md`); decisions should not sit uncommitted.
- Commit messages should still follow the conventional format
  (`<type>(<scope>): <description>`) from the global git steering, minus
  the Jira footer requirement.
- Revisit this file if the project later adopts Jira or branching (e.g. if
  collaborators join).
