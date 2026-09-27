#!/usr/bin/env python3
"""C_plumb_arg — find calls that drop a parameter the callee accepts.

Generic pattern: the public object has ``self.foo`` (or a local ``foo``)
and it calls ``inner(..., )`` without passing ``foo=...``, even though
the issue/test says ``foo`` is not forwarded. Add the keyword.

Project-agnostic. Candidate argument names are taken from the issue
("X is not passed") and from test assertions.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from _lib import Hit, func_at, issue_blob, iter_py_files, missing_args, parse_ast, print_hits, rel


def _call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _kw_names(node: ast.Call) -> set[str]:
    return {k.arg for k in node.keywords if k.arg}


def _self_attrs(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            out.add(node.attr)
    return out


def _mentioned_methods(blob: str) -> set[str]:
    # `structured_output()`, reduce_context, _format_request, ...
    import re
    return set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\s*\(", blob))


def scan(src_root: Path, blob: str) -> list[Hit]:
    args_wanted = missing_args(blob)
    methods = _mentioned_methods(blob)
    # Always consider these if the blob mentions them.
    for name in ("system_prompt", "invocation_state", "cache_prompt"):
        if name in blob:
            args_wanted.add(name)
    if not args_wanted:
        return []
    hits: list[Hit] = []
    for path in iter_py_files(src_root):
        tree = parse_ast(path)
        if tree is None:
            continue
        attrs = _self_attrs(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            cname = _call_name(node)
            ignore = {
                "ValueError", "TypeError", "Exception", "BedrockModel", "Agent",
                "print", "len", "range", "dict", "list", "super",
            }
            if cname in ignore:
                continue
            if methods:
                if cname not in methods and not any(cname.endswith(m) or m.endswith(cname) for m in methods):
                    continue
            kws = _kw_names(node)
            omitted = [a for a in args_wanted if a not in kws and a in attrs]
            if not omitted:
                continue
            # Skip if this call already has **kwargs that might forward them.
            has_kwargs = any(k.arg is None for k in node.keywords)
            if has_kwargs:
                continue
            hits.append(Hit(
                capability="C_plumb_arg",
                confidence="high" if cname in methods else "medium",
                file=rel(path, src_root.parent if src_root.name == "src" else src_root),
                line=getattr(node, "lineno", 1),
                symbol=func_at(tree, getattr(node, "lineno", 1)),
                why=(
                    f"{cname}() is called without {omitted}, but this class has "
                    f"self.{'/'.join(omitted)}"
                ),
                edit=(
                    "Add the missing keyword(s) on this call, e.g. "
                    + ", ".join(f"{a}=self.{a}" for a in omitted)
                    + "."
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
