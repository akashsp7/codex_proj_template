#!/usr/bin/env python3
"""
Generate a compact documentation context pack for the repo.

It includes:
- Root tree
- Python module docstring snapshot (focus configurable)
- List of Markdown docs + headings

This is meant to be consumed by an LLM to update docs without guessing.

Usage:
  python .codex/skills/update-documentation/scripts/docs_pack.py --out scratch/docs_pack.md
  python .codex/skills/update-documentation/scripts/docs_pack.py --focus src --out scratch/src_docs_pack.md
"""

from __future__ import annotations

import argparse
import ast
import io
import re
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
    "sessions",  # usually not needed for docs updates; remove if you want it included
}

DEFAULT_EXCLUDE_GLOBS = [
    "**/*.pyc",
    "**/.DS_Store",
]


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _matches_any_glob(rel_path: str, globs: Iterable[str]) -> bool:
    p = Path(rel_path)
    return any(p.match(g) for g in globs)


def _should_skip(rel_path: Path, is_dir: bool, exclude_dirs: set[str], exclude_globs: list[str]) -> bool:
    if any(part in exclude_dirs for part in rel_path.parts):
        return True
    if not is_dir and _matches_any_glob(str(rel_path), exclude_globs):
        return True
    return False


def build_tree_lines(root: Path, max_depth: int, exclude_dirs: set[str], exclude_globs: list[str]) -> list[str]:
    root = root.resolve()
    lines = [str(root)]

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
    try:
        with tokenize.open(path) as f:
            return f.read()
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")


def extract_module_docstring(source: str) -> str | None:
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
        return extract_module_docstring_fallback(source)


def extract_module_docstring_fallback(source: str) -> str | None:
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
                val = ast.literal_eval(tok.string)
                if isinstance(val, str):
                    val = val.strip("\n")
                    return val if val.strip() else None
            except Exception:
                raw = tok.string.strip("\n")
                return raw if raw.strip() else None

        return None

    return None


def truncate(text: str, max_lines: int, max_chars: int) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["… (truncated)"]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = out[: max_chars - 20].rstrip() + "\n… (truncated)"
    return out


def iter_python_files(root: Path, focus: Path, exclude_dirs: set[str], exclude_globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in focus.rglob("*.py"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if _should_skip(rel, False, exclude_dirs, exclude_globs):
            continue
        files.append(p)
    files.sort(key=lambda p: str(p).lower())
    return files


def iter_markdown_files(root: Path, exclude_dirs: set[str], exclude_globs: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*.md"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if _should_skip(rel, False, exclude_dirs, exclude_globs):
            continue
        files.append(p)
    files.sort(key=lambda p: str(p).lower())
    return files


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def extract_headings(md_text: str, max_headings: int) -> list[str]:
    out: list[str] = []
    for line in md_text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            title = m.group(2)
            out.append(("  " * (level - 1)) + f"- {title}")
            if len(out) >= max_headings:
                break
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Repo root (default: .)")
    ap.add_argument("--focus", default=".", help="Focus folder for Python docstrings (default: .)")
    ap.add_argument("--tree-depth", type=int, default=6, help="Tree depth (default: 6)")
    ap.add_argument("--max-docstring-lines", type=int, default=40, help="Docstring lines to include (default: 40)")
    ap.add_argument("--max-docstring-chars", type=int, default=2500, help="Docstring chars to include (default: 2500)")
    ap.add_argument("--max-md-headings", type=int, default=25, help="Headings per md file (default: 25)")
    ap.add_argument("--exclude-dir", action="append", default=[], help="Add excluded directory name (repeatable)")
    ap.add_argument("--exclude-glob", action="append", default=[], help="Add excluded glob (repeatable)")
    ap.add_argument("--out", required=True, help="Output file path (required)")
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

    tree_lines = build_tree_lines(root, args.tree_depth, exclude_dirs, exclude_globs)

    py_files = iter_python_files(root, focus, exclude_dirs, exclude_globs)

    py_blocks: list[str] = []
    missing: list[str] = []
    for p in py_files:
        rel = p.relative_to(root)
        src = _read_python_source(p)
        doc = extract_module_docstring(src)
        if doc is None:
            missing.append(str(rel))
            py_blocks.append(f"### {rel}\n\n_No module docstring found._\n")
        else:
            doc = truncate(doc, args.max_docstring_lines, args.max_docstring_chars)
            py_blocks.append(f"### {rel}\n\n```text\n{doc}\n```\n")

    md_files = iter_markdown_files(root, exclude_dirs, exclude_globs)
    md_blocks: list[str] = []
    for p in md_files:
        rel = p.relative_to(root)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = ""
        headings = extract_headings(text, args.max_md_headings)
        md_blocks.append(f"### {rel}\n")
        if headings:
            md_blocks.append("\n".join(headings) + "\n")
        else:
            md_blocks.append("_No headings found._\n")

    out = []
    out.append("# Docs context pack\n")
    out.append(f"**Root:** `{root}`  \n")
    out.append(f"**Focus (Python docstrings):** `{focus.relative_to(root)}`  \n")
    out.append(f"**Python files scanned:** {len(py_files)}  \n")
    out.append(f"**Markdown files found:** {len(md_files)}  \n")
    out.append(f"**Missing module docstrings:** {len(missing)}\n")

    out.append("## Repo tree\n")
    out.append("```text\n" + "\n".join(tree_lines) + "\n```\n")

    if missing:
        out.append("## Missing module docstrings\n")
        out.append("```text\n" + "\n".join(missing) + "\n```\n")

    out.append("## Python module docstrings\n")
    out.extend(py_blocks if py_blocks else ["_No Python files found._\n"])

    out.append("## Markdown docs headings\n")
    out.extend(md_blocks if md_blocks else ["_No Markdown files found._\n"])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
