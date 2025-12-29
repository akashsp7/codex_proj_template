#!/usr/bin/env python3
"""
Codebase snapshot utility.

Outputs:
- A tree view of the repository (cross-platform).
- Module docstrings for Python files (one-shot overview).

Usage examples:
  python .codex/skills/understand-codebase/scripts/codebase_snapshot.py
  python .codex/skills/understand-codebase/scripts/codebase_snapshot.py --focus src/graph --out scratch/graph_snapshot.md
  python .codex/skills/understand-codebase/scripts/codebase_snapshot.py --missing-only --fail-on-missing

Notes:
- "Module docstring" means: the first statement in the module is a string literal.
- Shebang/encoding/comments are fine above the docstring.
"""

from __future__ import annotations

import argparse
import ast
import io
import os
import sys
import textwrap
import tokenize
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    ".tox",
    ".eggs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


DEFAULT_EXCLUDE_GLOBS = [
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    "**/*.so",
    "**/*.dylib",
    "**/*.dll",
    "**/.DS_Store",
]


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _matches_any_glob(rel_path: str, globs: Iterable[str]) -> bool:
    # Path.match works on path parts; using it directly on rel Path is fine,
    # but for safety we also support glob-ish strings in a normalized way.
    p = Path(rel_path)
    return any(p.match(g) for g in globs)


def _should_skip(rel_path: Path, is_dir: bool, exclude_dirs: set[str], exclude_globs: list[str]) -> bool:
    parts = rel_path.parts
    if any(part in exclude_dirs for part in parts):
        return True
    # Skip hidden directories/files? Not by default: .codex is useful.
    # You can add ".codex" to exclude_dirs if desired.
    if not is_dir and _matches_any_glob(str(rel_path), exclude_globs):
        return True
    return False


def build_tree_lines(
    root: Path,
    max_depth: int,
    exclude_dirs: set[str],
    exclude_globs: list[str],
) -> list[str]:
    """
    Render a deterministic tree view.
    """
    root = root.resolve()
    label = str(root)

    lines: list[str] = [label]

    def walk(dir_path: Path, prefix: str, depth: int) -> None:
        if depth >= max_depth:
            return

        try:
            entries = list(dir_path.iterdir())
        except PermissionError:
            lines.append(prefix + "└── " + "[permission denied]")
            return

        filtered: list[Path] = []
        for p in entries:
            rel = p.relative_to(root)
            if _should_skip(rel, p.is_dir(), exclude_dirs, exclude_globs):
                continue
            filtered.append(p)

        # Sort: dirs first, then files; alpha insensitive
        filtered.sort(key=lambda p: (p.is_file(), p.name.lower()))

        for i, p in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            name = p.name + ("/" if p.is_dir() else "")
            lines.append(prefix + connector + name)

            if p.is_dir():
                extension = "    " if is_last else "│   "
                walk(p, prefix + extension, depth + 1)

    walk(root, "", 0)
    return lines


def _read_python_source(path: Path) -> str:
    # tokenize.open respects PEP 263 encoding cookies.
    try:
        with tokenize.open(path) as f:
            return f.read()
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_module_docstring(path: Path) -> str | None:
    """
    Extract module docstring using AST, fallback to token scanning if syntax errors exist.
    """
    source = _read_python_source(path)

    try:
        module = ast.parse(source)
        doc = ast.get_docstring(module, clean=False)
        if doc is None:
            return None
        doc = doc.strip("\n")
        return doc if doc.strip() else None
    except SyntaxError:
        return extract_module_docstring_fallback(source)
    except Exception:
        # If parsing explodes for a weird reason, attempt fallback anyway.
        return extract_module_docstring_fallback(source)


def extract_module_docstring_fallback(source: str) -> str | None:
    """
    Fallback: scan tokens and treat the first non-trivia STRING token as module docstring.
    """
    try:
        tokgen = tokenize.generate_tokens(io.StringIO(source).readline)
    except Exception:
        return None

    for tok in tokgen:
        if tok.type in (
            tokenize.ENCODING,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.COMMENT,
            tokenize.INDENT,
            tokenize.DEDENT,
        ):
            continue

        if tok.type == tokenize.STRING:
            try:
                value = ast.literal_eval(tok.string)
                if isinstance(value, str):
                    value = value.strip("\n")
                    return value if value.strip() else None
            except Exception:
                # Worst case: return the raw token text.
                raw = tok.string.strip("\n")
                return raw if raw.strip() else None

        # First real token is not a string => no module docstring
        return None

    return None


def truncate_block(text: str, max_lines: int, max_chars: int) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["… (truncated)"]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[: max_chars - 20].rstrip() + "\n… (truncated)"
    return out


def iter_python_files(root: Path, focus: Path, exclude_dirs: set[str], exclude_globs: list[str]) -> list[Path]:
    root = root.resolve()
    focus = focus.resolve()
    files: list[Path] = []

    for p in focus.rglob("*.py"):
        if not p.is_file():
            continue
        rel = p.relative_to(root) if _is_within(p, root) else p
        if _should_skip(rel if isinstance(rel, Path) else Path(str(rel)), False, exclude_dirs, exclude_globs):
            continue
        files.append(p)

    files.sort(key=lambda p: str(p).lower())
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repository root (default: .)")
    ap.add_argument("--focus", default=".", help="Folder under root to scan for .py docstrings (default: .)")
    ap.add_argument("--max-depth", type=int, default=6, help="Tree depth (default: 6)")
    ap.add_argument("--max-docstring-lines", type=int, default=60, help="Max docstring lines to print (default: 60)")
    ap.add_argument("--max-docstring-chars", type=int, default=4000, help="Max docstring characters (default: 4000)")
    ap.add_argument("--missing-only", action="store_true", help="Only print files missing module docstrings")
    ap.add_argument("--fail-on-missing", action="store_true", help="Exit non-zero if any module docstrings are missing")
    ap.add_argument("--exclude-dir", action="append", default=[], help="Add an excluded directory name (repeatable)")
    ap.add_argument("--exclude-glob", action="append", default=[], help="Add an excluded glob (repeatable)")
    ap.add_argument("--out", default="", help="Write output to a file instead of stdout")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    focus = (root / args.focus).resolve()

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root does not exist or is not a directory: {root}")

    if not focus.exists() or not focus.is_dir():
        raise SystemExit(f"Focus does not exist or is not a directory: {focus}")

    if not _is_within(focus, root):
        raise SystemExit(f"Focus must be inside root.\nroot={root}\nfocus={focus}")

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)
    exclude_globs = list(DEFAULT_EXCLUDE_GLOBS) + list(args.exclude_glob)

    tree_root_lines = build_tree_lines(root, args.max_depth, exclude_dirs, exclude_globs)
    focus_lines: list[str] = []
    if focus != root:
        focus_lines = build_tree_lines(focus, max(1, min(args.max_depth, 6)), exclude_dirs, exclude_globs)

    py_files = iter_python_files(root, focus, exclude_dirs, exclude_globs)

    missing: list[str] = []
    rendered_blocks: list[str] = []

    for p in py_files:
        rel = p.relative_to(root)
        doc = extract_module_docstring(p)

        if doc is None:
            missing.append(str(rel))

        if args.missing_only and doc is not None:
            continue

        header = f"### {rel}"
        if doc is None:
            body = "_No module docstring found._"
        else:
            trimmed = truncate_block(doc, args.max_docstring_lines, args.max_docstring_chars)
            body = "```text\n" + trimmed + "\n```"

        rendered_blocks.append(header + "\n\n" + body + "\n")

    out_parts: list[str] = []
    out_parts.append("# Codebase snapshot\n")
    out_parts.append(f"**Root:** `{root}`  \n")
    out_parts.append(f"**Focus:** `{focus.relative_to(root)}`  \n")
    out_parts.append(f"**Python files scanned:** {len(py_files)}  \n")
    out_parts.append(f"**Missing module docstrings:** {len(missing)}\n")

    out_parts.append("## Project tree (root)\n")
    out_parts.append("```text\n" + "\n".join(tree_root_lines) + "\n```\n")

    if focus_lines:
        out_parts.append("## Focus tree\n")
        out_parts.append("```text\n" + "\n".join(focus_lines) + "\n```\n")

    if missing:
        out_parts.append("## Missing module docstrings\n")
        out_parts.append("```text\n" + "\n".join(missing) + "\n```\n")

    out_parts.append("## Module docstrings\n")
    if rendered_blocks:
        out_parts.extend(rendered_blocks)
    else:
        out_parts.append("_No Python files found in focus._\n")

    output = "\n".join(out_parts)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(str(out_path))
    else:
        print(output)

    if args.fail_on_missing and missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
