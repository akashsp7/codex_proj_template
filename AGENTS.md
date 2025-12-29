# Codex Operator Manual

## Prime directive

Work in small, testable increments. Prefer simple, explicit code over clever code.

## Before you touch code

1. Read: README.md, TODO.md, decisions.md, learnings.md
2. Read the latest session in /sessions (if any)
3. Create a new session log in /sessions for this run (see the session protocol below)

## Session protocol

- Start of session:
  - Create a new session file in /sessions with today’s date + short title.
  - Add: goal, plan, current state, and “definition of done”.
- During session:
  - Log major steps and outcomes (especially surprising ones).
  - If you discover new work, add it to TODO.md.
  - If you make a meaningful choice, record it in decisions.md with rationale.
  - If you hit a pitfall, add it to learnings.md.
- End of session:
  - Summarize what changed, what’s still broken, and next actions.

## Coding standards

- Keep functions small and composable.
- Prefer pure functions for core logic; isolate I/O and side effects.
- Add type hints for public functions/classes and key internal boundaries.
- Comments must explain intent, constraints, or “why”, not restate code.
- Add input validation and error handling at boundaries (network/files/tools).
- No secrets committed. Use .env and provide .env.example when needed.

## Testing standards

- Write/extend unit tests for core logic.
- Add at least one integration test for any multi-component flow.
- When changing behavior, update tests first or alongside code.
- Always run the relevant test subset before finishing.

## Module docstring contract (Python)

Every Python file must begin with a module docstring (after shebang/encoding comments if present).
It should be kept accurate as the file evolves.

Preferred structure:

"""
Purpose:

- What this module does in 1 to 3 bullets.

Key responsibilities:

- What it owns (and does NOT own).

Public API:

- List the functions/classes intended for external use (names only).

Dependencies:

- External systems, files, env vars, config keys, network calls.

Notes:

- Gotchas, invariants, performance constraints, security concerns.

Example:

- Minimal usage snippet (optional).
  """

## Repo conventions

- /src contains production code
- /tests contains tests
- /scratch contains throwaway prototypes (keep it messy on purpose)
- /sessions is the work journal; keep entries short but factual

## Working style

- When asked to implement something:
  1. restate constraints
  2. propose a small plan
  3. implement smallest slice
  4. test it
  5. iterate

## Skills available in this repo

- $session-journal: create and maintain session logs
