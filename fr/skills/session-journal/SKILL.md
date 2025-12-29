---
name: session-journal
description: Create and maintain session logs in /sessions and keep TODO/decisions/learnings aligned.
metadata:
  short-description: Session logging ritual (start + end).
---

## When to use

- At the start of any new Codex session in this repo.
- When resuming work after a break.
- Before you finish, to write a clean summary and next steps.

## Start of session steps

1. Read TODO.md, decisions.md, learnings.md
2. Read the most recent file in /sessions (if any)
3. Create a new session file by running:
   python .codex/skills/session-journal/scripts/new_session.py "<short title>"
4. Open the created session file and fill in:
   - Goal
   - Plan
   - Definition of Done
   - Current state

## End of session steps

1. Update the session file:
   - What changed
   - What was validated (tests, manual checks)
   - Remaining issues
   - Next steps (concrete)
2. If any decision was made, append it to decisions.md
3. If any new pitfall/learning occurred, append it to learnings.md
4. Update TODO.md:
   - Mark done items
   - Add new items discovered
