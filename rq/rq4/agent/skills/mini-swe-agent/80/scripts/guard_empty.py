#!/usr/bin/env python3
"""C_normalize_empty — find fields forwarded to an API without an empty guard.

Generic pattern: a dict field (often ``content``) is iterated or passed
through even when it can be ``[]``. Downstream validators then reject
the payload. Insert ``if not field: field = [<non-empty placeholder>]``
at the format / serialize boundary.

Project-agnostic: field names come from the issue/test, defaulting to
common payload keys.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _lib import (
    Hit,
    empty_fields,
    func_at,
    issue_blob,
    iter_py_files,
    parse_ast,
    print_hits,
    rel,
)


_DEFAULT_FIELDS = {"content", "messages", "items", "data", "body"}


def _field_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            return sl.value
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
    return None


def scan(src_root: Path, blob: str) -> list[Hit]:
    mentioned = empty_fields(blob)
    talks_empty = bool(mentioned) or (
        "empty" in blob.lower() and ("[]" in blob or "content" in blob.lower())
    )
    if not talks_empty:
        return []
    fields = mentioned or {"content"}
    hits: list[Hit] = []
    for path in iter_py_files(src_root):
        tree = parse_ast(path)
        if tree is None:
            continue
        src = path.read_text(errors="ignore")
        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue
            fname = _field_name(node.iter)
            if fname not in fields:
                continue
            sym = func_at(tree, getattr(node, "lineno", 1))
            seg = "\n".join(src.splitlines()[max(0, node.lineno - 12): node.lineno + 8])
            high = (
                "format" in (sym or "").lower()
                or "toolResult" in seg
                or "tool_result" in seg
            )
            hits.append(Hit(
                capability="C_normalize_empty",
                confidence="high" if high else "medium",
                file=rel(path, src_root.parent if src_root.name == "src" else src_root),
                line=getattr(node, "lineno", 1),
                symbol=sym,
                why=(
                    f"iterates {fname!r} with no empty-array guard; "
                    f"issue mentions empty {sorted(fields)}"
                ),
                edit=(
                    f"Before the loop, if the {fname} list is empty, replace it "
                    f"with a one-element placeholder the downstream API accepts "
                    f"(e.g. [{{'text': ''}}] for chat content)."
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
