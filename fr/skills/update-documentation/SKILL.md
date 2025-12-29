---
name: update-documentation
description: Refresh README(s) and TODO based on the real codebase. Uses a generated context pack to avoid hallucinating features.
metadata:
  short-description: Audit + update docs from code.
---

## When to use

- After implementing a feature or refactor
- Before a release / handoff
- When docs feel stale

## Non-negotiables

- Never invent behavior. If it isn't visible in code, label it "unknown" and add a TODO.
- Prefer short, accurate docs over long, speculative docs.
- Keep README focused on: what it is, how to run, how to test, architecture at a glance.

## Steps

1. Generate a context pack:
   python .codex/skills/update-documentation/scripts/docs_pack.py --out scratch/docs_pack.md

2. Use scratch/docs_pack.md + direct file reads (README.md, TODO.md, docs/) to update:

   - README.md (and any nested README.md files if present)
   - TODO.md (add newly discovered work, mark done items)
   - Optional: docs/ARCHITECTURE.md (if your repo uses /docs)

3. Cross-check:

   - Does README mention modules that do not exist? Remove or fix.
   - Are there new modules or entrypoints that README does not mention? Add.
   - Are setup steps accurate (deps, env vars, commands)?

4. Log:
   - Any decisions => decisions.md
   - Any pitfalls discovered => learnings.md
