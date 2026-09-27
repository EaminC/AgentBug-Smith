#!/usr/bin/env python3
"""localize.py — Resolve a failing test to the source file(s) to edit.

Given any Python test file, extract its ``from X import Y`` statements
and resolve each ``Y`` to its defining file. Uses:

  1. ``python -c "import X; print(X.__file__)"`` for proper packages, OR
  2. Recursive grep for ``^class Y\\b|^def Y\\b|^Y =`` for monorepos where
     the import goes through a re-export.

This is a project-agnostic step: it works on any Python repository
whose source lives under ``src/`` (or any other tree passed via
``--src``).

Usage::

  python3 scripts/localize.py \\
      --test tests/<TEST_FILE>.py \\
      --src  src/

Output (stdout)::

  tests/<TEST_FILE>.py → <module>.<symbol>: <relative/path>.py

The agent then opens each output file and picks the one whose context
matches the failing assertion. The script intentionally stops at
file-level resolution — line-level edits are ``edit.py``'s job.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

_REPO_FROM_IMPORT = re.compile(r"^from\s+([\w.]+)\s+import\s+(.+)$")
_IMPORT = re.compile(r"^\s*import\s+([\w.]+)\s*$")


def _imports_in(test_path: Path) -> list[tuple[str, str]]:
    """Return ``[(module, symbol), ...]`` from the test's import statements."""
    src = test_path.read_text(errors="ignore")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for nm in node.names:
                out.append((node.module, nm.name))
        elif isinstance(node, ast.Import):
            for nm in node.names:
                out.append((nm.name, nm.name.split(".")[0]))
    return out


def _resolve_via_importlib(module: str) -> Path | None:
    """Best-effort: ``python -c "import X; print(X.__file__)"``."""
    try:
        out = subprocess.run(
            ["python3", "-c",
             f"import sys; sys.path.insert(0, '.'); "
             f"import {module} as m; print(getattr(m, '__file__', '') or ''); "
             f"print(getattr(m, '__path__', [''])[0] or '')"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode == 0:
            for ln in out.stdout.splitlines():
                ln = ln.strip()
                if ln and Path(ln).exists():
                    return Path(ln)
    except Exception:
        return None
    return None


def _grep_for_symbol(symbol: str, src_root: Path) -> list[Path]:
    """Recursive grep: find files that define ``symbol``."""
    candidates = []
    for ext in ("*.py", "*.pyx"):
        for p in src_root.rglob(ext):
            try:
                txt = p.read_text(errors="ignore")
            except OSError:
                continue
            for pat in (
                re.compile(rf"^(class|def|async def)\s+{re.escape(symbol)}\b", re.MULTILINE),
                re.compile(rf"^{re.escape(symbol)}\s*[:=]", re.MULTILINE),
            ):
                for m in pat.finditer(txt):
                    candidates.append((p, txt[: m.start()].count("\n") + 1))
                    break
    # Drop duplicates but keep first-occurrence ordering.
    seen = set()
    uniq = []
    for p, ln in candidates:
        if p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    return uniq


_NAME = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b")
_METHODISH = re.compile(r"\b(_?[a-z][A-Za-z0-9_]{3,})\(")
_SKIP_MODS = {
    "pytest", "unittest", "os", "sys", "re", "json", "typing", "pathlib",
    "asyncio", "functools", "collections", "dataclasses", "enum", "abc",
    "pydantic", "botocore", "boto3", "mock", "unittest.mock",
}


def _symbols_from_text(text: str) -> list[str]:
    """Names the test/issue actually mentions — better than imports alone."""
    out: list[str] = []
    for m in _METHODISH.finditer(text):
        name = m.group(1)
        if name in {"test", "pytest", "print", "len", "range", "list", "dict", "super"}:
            continue
        out.append(name)
    return list(dict.fromkeys(out))


def localize(test_path: Path, src_root: Path, extra_text: str = "") -> list[tuple[str, Path, int]]:
    """Return ``[(module.symbol, file, line), ...]`` for every import + mention."""
    out = []
    src_root = src_root.resolve()
    for mod, sym in _imports_in(test_path):
        if mod.split(".")[0] in _SKIP_MODS:
            continue
        # Prefer a file that actually lives under --src. Host site-packages
        # (or a newer checkout of the same package) are the wrong tree.
        f = _resolve_via_importlib(mod)
        if f and f.exists():
            try:
                rel = f.resolve().relative_to(src_root)
                out.append((f"{mod}.{sym}", rel, 1))
                continue
            except ValueError:
                pass
        cands = _grep_for_symbol(sym, src_root)
        for c in cands[:2]:
            try:
                rel = c.resolve().relative_to(src_root)
            except ValueError:
                rel = c
            out.append((f"{mod}.{sym}", rel, 1))
    # Also resolve method names cited in the test / issue (e.g. reduce_context).
    blob = test_path.read_text(errors="ignore") + "\n" + extra_text
    for name in _symbols_from_text(blob):
        if any(t[0].endswith("." + name) or t[0] == name for t in out):
            continue
        cands = _grep_for_symbol(name, src_root)
        for c in cands[:2]:
            out.append((name, c, 1))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", required=True, type=Path,
                    help="Path to the failing f2p test file")
    ap.add_argument("--src", required=True, type=Path,
                    help="Path to the source tree (e.g. src/)")
    ap.add_argument("--issue", type=Path, default=None,
                    help="Optional issue.json; method names in title/body are also resolved")
    args = ap.parse_args()

    extra = ""
    if args.issue and args.issue.exists():
        extra = args.issue.read_text(errors="ignore")
    pairs = localize(args.test, args.src, extra)
    if not pairs:
        print("NO_LOCALIZE", file=sys.stderr)
        sys.exit(2)
    for sym, f, _ in pairs:
        print(f"{args.test} → {sym}: {f}")
    sys.exit(0)


if __name__ == "__main__":
    main()
