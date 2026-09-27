#!/usr/bin/env python3
"""C_widen_match — find identifier predicates that are too narrow.

Generic pattern: ``return "foo" in s or "bar" in s``. If the issue/test
mentions another identifier token that is *not* in the predicate (ARN
path, profile id, vendor prefix), the check will silently fail for
that identifier.

This is project-agnostic. It does not know about Bedrock or any repo.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _lib import (
    Hit,
    extract_tokens,
    func_at,
    issue_blob,
    iter_py_files,
    parse_ast,
    print_hits,
    rel,
)


def _in_strings(node: ast.AST) -> list[str]:
    found: list[str] = []
    if isinstance(node, ast.Compare) and any(isinstance(op, ast.In) for op in node.ops):
        left = node.left
        if isinstance(left, ast.Constant) and isinstance(left.value, str):
            found.append(left.value)
    if isinstance(node, ast.BoolOp):
        for v in node.values:
            found.extend(_in_strings(v))
    return found


def scan(src_root: Path, blob: str) -> list[Hit]:
    tokens = {t.lower() for t in extract_tokens(blob)}
    hits: list[Hit] = []
    for path in iter_py_files(src_root):
        tree = parse_ast(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            needles = _in_strings(node.value)
            if len(needles) < 1:
                continue
            have = {n.lower() for n in needles}
            missing = [
                t for t in tokens
                if t not in have
                and any(ch in t for ch in "/-:_")
                and not t.startswith("test_")
                and "\n" not in t
                and len(t) >= 8
            ][:4]
            if not missing:
                continue
            conf = "high"
            hits.append(Hit(
                capability="C_widen_match",
                confidence=conf,
                file=rel(path, src_root.parent if src_root.name == "src" else src_root),
                line=getattr(node, "lineno", 1),
                symbol=func_at(tree, getattr(node, "lineno", 1)),
                why=(
                    f"predicate only matches {needles!r}; issue mentions {missing!r}"
                ),
                edit=(
                    "Widen the `in` check with the missing identifier token, "
                    "or add an alternate lookup (ARN / profile / alias) instead "
                    "of relying on a substring of the raw id."
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
