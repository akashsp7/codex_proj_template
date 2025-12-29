---
name: understand-codebase
description: Produce a one-shot codebase overview (root tree + module docstrings for Python files). Supports focusing on a folder.
metadata:
  short-description: Tree + module docstrings snapshot.
---

## When to use

- At the start of a session, before making architectural changes
- When you feel "lost" in the repo
- Before updating documentation

## What to do

1. Generate a snapshot for the whole repo:
   python .codex/skills/understand-codebase/scripts/codebase_snapshot.py --out scratch/codebase_snapshot.md

2. Or focus on a folder (docstrings only from that folder, but still show root tree):
   python .codex/skills/understand-codebase/scripts/codebase_snapshot.py --focus src/graph --out scratch/graph_snapshot.md

3. If you want to enforce module docstrings:
   python .codex/skills/understand-codebase/scripts/codebase_snapshot.py --missing-only --fail-on-missing

## Output expectations

- Do not include any code beyond module docstrings
- Report missing module docstrings clearly
- Keep output compact (trim very long docstrings)
