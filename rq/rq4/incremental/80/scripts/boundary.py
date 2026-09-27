#!/usr/bin/env python3
"""C_boundary_zero — find numeric params used as ``len(x) - n`` with no n==0.

Generic pattern: a size/window/limit parameter is subtracted from
``len(...)`` or used as a loop bound. ``n=0`` then becomes
"trim_index == len" and the loop never runs, so the empty/clear case
silently fails. Handle ``n < 0`` (reject) and ``n == 0`` (clear / no-op)
before the loop.

Project-agnostic.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _lib import Hit, func_at, issue_blob, iter_py_files, mentions_zero, parse_ast, print_hits, rel


_SIZE_NAMES = {
    "window_size", "size", "limit", "max_size", "n", "k", "count",
    "max_tokens", "width", "capacity",
}


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_len_minus(node: ast.AST) -> str | None:
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub)):
        return None
    if isinstance(node.left, ast.Call) and _name(node.left.func) == "len":
        return _name(node.right)
    return None


def _fn_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    args = node.args
    names = {a.arg for a in args.args + args.kwonlyargs}
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)
    return names


def scan(src_root: Path, blob: str) -> list[Hit]:
    if not mentions_zero(blob):
        return []
    hits: list[Hit] = []
    for path in iter_py_files(src_root):
        tree = parse_ast(path)
        if tree is None:
            continue
        src = path.read_text(errors="ignore")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = _fn_params(node)
            size_params = (params & _SIZE_NAMES) | {
                p for p in params if p.endswith("_size") or p.endswith("_limit")
            }
            uses: list[tuple[int, str]] = []
            guards: set[str] = set()
            for child in ast.walk(node):
                name = _is_len_minus(child)
                if name:
                    uses.append((getattr(child, "lineno", node.lineno), name))
                if isinstance(child, ast.Compare):
                    lhs = _name(child.left)
                    if lhs and any(isinstance(op, (ast.Eq, ast.Lt, ast.LtE, ast.NotEq)) for op in child.ops):
                        if any(isinstance(c, ast.Constant) and c.value in (0, -1) for c in child.comparators):
                            guards.add(lhs)
                if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Sub):
                    right = _name(child.right)
                    left_has_len = isinstance(child.left, ast.Call) and _name(child.left.func) == "len"
                    if left_has_len and right:
                        uses.append((getattr(child, "lineno", node.lineno), right))
            for lineno, name in uses:
                if name in guards:
                    continue
                if name not in _SIZE_NAMES and name not in size_params and name not in {"window_size", "self"}:
                    # attribute.attr already reduced to attr
                    if name not in _SIZE_NAMES and not (name and name.endswith("_size")):
                        continue
                hits.append(Hit(
                    capability="C_boundary_zero",
                    confidence="high",
                    file=rel(path, src_root.parent if src_root.name == "src" else src_root),
                    line=lineno,
                    symbol=func_at(tree, lineno),
                    why=(
                        f"{name} is used as len(x)-{name} with no {name}==0 / {name}<0 guard"
                    ),
                    edit=(
                        f"Before the trim/loop: reject {name}<0; if {name}==0, clear the "
                        f"collection (or take the documented empty-window behaviour) and return."
                    ),
                ))
    # Dedup by file:line
    seen = set()
    uniq = []
    for h in hits:
        key = (h.file, h.line, h.symbol)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
    return uniq


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
