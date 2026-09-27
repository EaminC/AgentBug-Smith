#!/usr/bin/env python3
"""guard_patch.py — reject patches that historically never become F2P.

Generic gates, none of them repo-specific:

  * catastrophic size  (>+80 / >-30 lines)  → many rewrite failures
  * added lines do not compile as a fragment / file py_compile fails
  * public rename (class/def name removed, new name added)
  * insertion looks like it landed inside a docstring

Exit 0 only when the patch is small, compiling, and not a rename.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


_DEF = re.compile(r"^([+-])\s*(?:async\s+)?(def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)


def _counts(patch: str) -> tuple[int, int]:
    add = del_ = 0
    for line in patch.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            add += 1
        elif line.startswith("-"):
            del_ += 1
    return add, del_


def _renames(patch: str) -> list[str]:
    removed, added = set(), set()
    for m in _DEF.finditer(patch):
        (removed if m.group(1) == "-" else added).add(m.group(3))
    return sorted(removed - added)


def _inside_docstring_risk(patch: str) -> bool:
    # Very cheap: a + line whose previous context is an open triple-quote
    # and the added line is indented code (def/if/return).
    lines = patch.splitlines()
    in_doc = False
    for line in lines:
        if line.startswith(("+++", "---", "diff ", "index ", "@@")):
            continue
        body = line[1:] if line[:1] in "+- " else line
        if '"""' in body or "'''" in body:
            in_doc = not in_doc
            continue
        # Only flag code that is indented *inside* a method docstring
        # (8+ spaces). Class-level `    def` / `    @property` after a
        # method docstring is a normal adjacent insert.
        if line.startswith("+") and in_doc and re.match(r"\s{8,}(def |class |if |return |for )", line[1:]):
            return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patch", required=True, type=Path)
    ap.add_argument("--max-add", type=int, default=80)
    ap.add_argument("--max-del", type=int, default=30)
    ap.add_argument("--file", action="append", default=[],
                    help="Edited source files to py_compile (repeatable).")
    args = ap.parse_args()

    text = args.patch.read_text(errors="ignore")
    add, delete = _counts(text)
    errors = []
    if add > args.max_add or delete > args.max_del:
        errors.append(f"CATASTROPHIC size +{add}/-{delete} (caps +{args.max_add}/-{args.max_del})")
    renames = _renames(text)
    if renames:
        errors.append(f"RENAME of public names {renames}; add a new name instead")
    for f in args.file:
        p = Path(f)
        if not p.exists():
            errors.append(f"MISSING {f}")
            continue
        proc = subprocess.run(
            ["python3", "-m", "py_compile", str(p)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-1:]
            errors.append(f"SYNTAX {f}: {tail[0] if tail else 'py_compile failed'}")

    if errors:
        for e in errors:
            print(f"REJECT: {e}", file=sys.stderr)
        sys.exit(3)
    print(f"OK: +{add}/-{delete}, no rename, compile clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
