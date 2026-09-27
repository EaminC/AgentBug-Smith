#!/usr/bin/env python3
"""C_fallback_path — find skip-loops that raise when nothing matches.

Generic pattern (Python ``for``/``else``): a loop skips every candidate
(``continue`` / no ``break``) and the ``else`` raises or warns
"unable to …". When the primary filter is too strict, there is no
valid cut point. Add a *fallback* pass before the raise.

Project-agnostic. Works on any Python file with for/else + raise.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _lib import Hit, func_at, issue_blob, iter_py_files, parse_ast, print_hits, rel


_RAISE_HINTS = ("unable", "cannot", "can't", "no valid", "failed to", "could not")


def _else_is_failure(orelse: list[ast.stmt], src: str) -> bool:
    if not orelse:
        return False
    text = " ".join(ast.get_source_segment(src, n) or "" for n in orelse).lower()
    for n in orelse:
        if isinstance(n, ast.Raise):
            return True
        if isinstance(n, ast.Expr) and "warning" in text:
            return True
    return any(h in text for h in _RAISE_HINTS)


def scan(src_root: Path, blob: str) -> list[Hit]:
    want = any(k in blob.lower() for k in (
        "unable to", "no valid", "fallback", "fails to trim", "cannot trim",
        "no trim", "tool-heavy", "trim conversation", "overflow",
    ))
    if not want:
        return []
    hits: list[Hit] = []
    for path in iter_py_files(src_root):
        tree = parse_ast(path)
        if tree is None:
            continue
        src = path.read_text(errors="ignore")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While)) or not node.orelse:
                continue
            if not _else_is_failure(node.orelse, src):
                continue
            hits.append(Hit(
                capability="C_fallback_path",
                confidence="high" if want else "medium",
                file=rel(path, src_root.parent if src_root.name == "src" else src_root),
                line=getattr(node, "lineno", 1),
                symbol=func_at(tree, getattr(node, "lineno", 1)),
                why=(
                    "for/else raises or warns when the primary filter skips "
                    "every candidate — no fallback cut exists"
                ),
                edit=(
                    "Before the raise/return in the `else`, run a more lenient "
                    "fallback (e.g. a paired boundary the primary filter rejected) "
                    "and only raise if that also finds nothing."
                ),
            ))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--issue", type=Path, default=None)
    ap.add_argument("--test", type=Path, default=None)
    args = ap.parse_args()
    extra = args.test.read_text(errors="ignore") if args.test and args.test.exists() else ""
    blob = issue_blob(args.issue, extra)
    sys.exit(print_hits(scan(args.src, blob)))


if __name__ == "__main__":
    main()
