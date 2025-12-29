#!/usr/bin/env python3
"""
Create a new session markdown file in /sessions.

Usage:
  python .codex/skills/session-journal/scripts/new_session.py "fix auth retry logic"
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "session"


def next_index(sessions_dir: Path) -> int:
    """
    Finds the next numeric prefix like 0007-YYYY-MM-DD--title.md
    """
    max_idx = 0
    for p in sessions_dir.glob("*.md"):
        m = re.match(r"^(\d{4})-", p.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    return max_idx + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("title", nargs="*", help="Optional session title")
    ap.add_argument("--dir", default="sessions", help="Sessions directory (default: sessions)")
    ap.add_argument("--no-index", action="store_true", help="Do not prefix with numeric index")
    args = ap.parse_args()

    sessions_dir = Path(args.dir)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    title = " ".join(args.title).strip() or "work session"
    slug = slugify(title)

    today = dt.date.today().isoformat()
    now = dt.datetime.now().strftime("%H:%M")

    idx = None if args.no_index else next_index(sessions_dir)

    prefix = f"{idx:04d}-" if idx is not None else ""
    filename = f"{prefix}{today}--{slug}.md"
    path = sessions_dir / filename

    # Ensure uniqueness if you run it twice quickly
    if path.exists():
        stamp = dt.datetime.now().strftime("%H%M%S")
        filename = f"{prefix}{today}--{slug}--{stamp}.md"
        path = sessions_dir / filename

    header_id = f"{idx:04d} " if idx is not None else ""
    content = f"""# Session {header_id}- {today} - {title}

**Started:** {today} {now}

## Goal
- 

## Plan
- [ ] 

## Definition of done
- 

## Context
- Links:
- Constraints:

## Work log
- {today} {now} - Session created.

## Decisions
- (Record any decisions here, then also copy to /decisions.md)

## Learnings
- (Record any learnings here, then also copy to /learnings.md)

## Next steps
- [ ] 
"""

    path.write_text(content, encoding="utf-8")
    print(str(path))


if __name__ == "__main__":
    main()
