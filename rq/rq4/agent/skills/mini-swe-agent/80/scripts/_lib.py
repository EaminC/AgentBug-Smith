#!/usr/bin/env python3
"""Shared helpers for the generic capability scanners."""
from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Hit:
    capability: str
    confidence: str  # high | medium | low
    file: str
    line: int
    symbol: str
    why: str
    edit: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


_TOKEN = re.compile(
    r"(?:application-inference-profile|/v1|[A-Za-z_][A-Za-z0-9_]{2,}"
    r"|arn:[a-z0-9:-]+|[a-z]+(?:-[a-z0-9]+){2,})",
)
_QUOTED = re.compile(r"""['"]([^'"]{3,80})['"]""")
_NOT_PASSED = re.compile(
    r"(?P<arg>[A-Za-z_][A-Za-z0-9_]*)\s+(?:is\s+)?not\s+passed"
    r"|not\s+pass(?:ed)?\s+(?:the\s+)?(?P<arg2>[A-Za-z_][A-Za-z0-9_]*)",
    re.I,
)
_ZERO = re.compile(r"\b(\w+_size|\w+_count|window|limit|n|k)\s*=\s*0\b", re.I)
_EMPTY_FIELD = re.compile(
    r"""(?:empty|missing)\s+['"]?([A-Za-z_][A-Za-z0-9_]*)['"]?"""
    r"""|['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*[:=]\s*\[\s*\]""",
    re.I,
)


def iter_py_files(src_root: Path) -> Iterable[Path]:
    skip = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}
    for p in src_root.rglob("*.py"):
        if any(part in skip for part in p.parts):
            continue
        yield p


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


def parse_ast(path: Path) -> ast.AST | None:
    src = read_text(path)
    if not src:
        return None
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def issue_blob(issue_path: Path | None, extra: str = "") -> str:
    parts = [extra]
    if issue_path and issue_path.exists():
        raw = read_text(issue_path)
        try:
            obj = json.loads(raw)
            parts.append(str(obj.get("title") or ""))
            parts.append(str(obj.get("body") or ""))
        except json.JSONDecodeError:
            parts.append(raw)
    return "\n".join(parts)


def extract_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for m in _QUOTED.finditer(text):
        out.add(m.group(1))
    for m in _TOKEN.finditer(text):
        tok = m.group(0)
        if tok.lower() in {"the", "and", "for", "this", "that", "with", "from"}:
            continue
        out.add(tok)
    return out


def missing_args(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NOT_PASSED.finditer(text):
        out.add(m.group("arg") or m.group("arg2"))
    # Common plumbing names if the issue talks about them not being forwarded.
    for name in ("system_prompt", "invocation_state", "cache_config", "timeout"):
        if name in text and re.search(rf"{name}.{{0,40}}(not|never|missing|isn't|is not)", text, re.I):
            out.add(name)
    return {a for a in out if a}


def empty_fields(text: str) -> set[str]:
    out = set()
    if re.search(r"content:\s*\[\s*\]|empty\s+(content|array|list)|toolResult.*content", text, re.I):
        out.add("content")
    return out


def mentions_zero(text: str) -> bool:
    return bool(_ZERO.search(text) or re.search(r"\b(window_size|size)\s*=\s*0\b", text))


def func_at(tree: ast.AST, lineno: int) -> str:
    best = ""
    best_line = -1
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if getattr(node, "lineno", 10**9) <= lineno and node.lineno >= best_line:
                best = node.name
                best_line = node.lineno
    return best


def print_hits(hits: list[Hit]) -> int:
    if not hits:
        print("NO_HIT")
        return 2
    rank = {"high": 0, "medium": 1, "low": 2}
    hits = sorted(hits, key=lambda h: (rank.get(h.confidence, 9), h.file, h.line))
    for h in hits:
        print(h.to_json())
    return 0
