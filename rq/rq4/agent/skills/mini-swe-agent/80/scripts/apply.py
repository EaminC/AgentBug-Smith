#!/usr/bin/env python3
"""apply.py — Apply a unified-diff patch to a checkout, with fallbacks.

Tries ``git apply`` first, falls back to ``git apply -3`` (3-way merge),
then to ``patch -p1``. After it succeeds it always runs ``py_compile``
on every Python file the patch touched.

Usage::

  apply.py --patch PATH [--repo PATH] [--strict]

  # ``--strict`` disables the 3-way fallback (use when the harness
  # verifies the exact diff). Default: lenient.

This is the LAST step before the f2p test. If ``apply.py`` succeeds
the agent should immediately invoke ``verify.py f2p``.

Example::

  $ apply.py --patch /tmp/final.patch
  OK: applied 1 file (3 hunks), py_compile passed
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_PY_FILE = re.compile(r"\+\+\+ b/(.+?\.py)\s*$", re.MULTILINE)


def _touched_py_files(patch_text: str) -> list[Path]:
    return [Path(m.group(1)) for m in _PY_FILE.finditer(patch_text)]


def _py_compile_all(paths: list[Path]) -> bool:
    for p in paths:
        if not p.exists():
            continue
        proc = subprocess.run(
            ["python3", "-m", "py_compile", str(p)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            sys.stderr.write(f"py_compile FAIL {p}:\n{proc.stderr}\n")
            return False
    return True


def apply(patch_path: Path, repo_dir: Path | None, strict: bool) -> int:
    text = patch_path.read_text()
    # Normalize common encodings that break `git apply`.
    text = (text.replace("\u00a0", " ")
                  .replace("\u200b", "")
                  .replace("\r\n", "\n"))
    patch_path.write_text(text)

    cwd = str(repo_dir) if repo_dir else "."
    cmds = [["git", "apply", "--ignore-space-change",
             "--ignore-whitespace", "--whitespace=nowarn", str(patch_path)]]
    if not strict:
        cmds.append(["git", "apply", "-3",
                     "--ignore-space-change", "--ignore-whitespace",
                     "--whitespace=nowarn", str(patch_path)])
        cmds.append(["patch", "-p1", "--ignore-whitespace", "-f", "-i", str(patch_path)])

    last_proc = None
    for cmd in cmds:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        last_proc = proc
        if proc.returncode == 0:
            touched = _touched_py_files(text)
            if not _py_compile_all(touched):
                return 3
            print(f"OK: applied via {cmd[0]} ({len(_PY_FILE.findall(text))} file(s))")
            return 0
    sys.stderr.write(
        f"FAILED: tried {[c[0] for c in cmds]}; last stderr:\n"
        f"{(last_proc.stderr if last_proc else '') or (last_proc.stdout if last_proc else '')}\n"
    )
    return 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patch", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=None)
    ap.add_argument("--strict", action="store_true",
                    help="Disable 3-way merge fallback.")
    args = ap.parse_args()
    sys.exit(apply(args.patch, args.repo, args.strict))


if __name__ == "__main__":
    main()
