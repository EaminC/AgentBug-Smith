#!/usr/bin/env python3
"""verify.py — Verify a patch in two stages: py_compile then f2p test.

Three sub-commands:

  * ``compile``     — run ``python -m py_compile`` on one or more files.
  * ``async-check`` — extra sanity for files with ``async def`` / ``await``.
  * ``f2p``         — run the failing test and report pass/fail.

The dominant verify op across the training set is ``V_py_compile_only``
(≈88% of hunks); the rest are async, raise-branch, or concurrency.
``compile`` catches the former; ``async-check`` is a cheap heuristic for
the latter.

Usage::

  # Stage 1 (always): py_compile every edited file.
  verify.py compile --file PATH [--file PATH...]

  # Optional: extra check for async changes.
  verify.py async-check --file PATH

  # Stage 2: run the f2p test (docker if --image given, else local pytest).
  verify.py f2p --test tests/<TEST_FILE>.py [--image <IMG>]

Exit codes:

  compile     → 0 if all files compile, 3 with first syntax error otherwise.
  async-check → 0 always; prints a warning if await/def ratio is suspicious.
  f2p         → 0 on PASS (docker) or LOCAL_PASS (no docker), 1 on FAIL,
                2 on missing test.

When ``f2p`` falls back to local pytest it prints ``LOCAL_PASS`` rather
than ``PASS`` — agents and harnesses can distinguish this from the
docker-grade verdict.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def cmd_compile(args) -> int:
    paths = [Path(p) for p in args.file]
    failed = []
    for p in paths:
        if not p.exists():
            sys.stderr.write(f"MISSING: {p}\n")
            failed.append((p, "file not found"))
            continue
        proc = subprocess.run(
            ["python3", "-m", "py_compile", str(p)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            failed.append((p, proc.stderr.strip().splitlines()[-1] if proc.stderr else ""))
    if failed:
        for p, err in failed:
            sys.stderr.write(f"FAIL {p}: {err}\n")
        return 3
    for p in paths:
        print(f"OK: {p}")
    return 0


def cmd_async_check(args) -> int:
    """Extra check for files with ``async def`` / ``await`` additions."""
    p = Path(args.file)
    txt = p.read_text()
    if "async def" in txt or "await " in txt:
        # Cheap sanity: count of `async def` and check balanced awaits.
        adef = len(re.findall(r"^\s*(async def|def)\b", txt, re.MULTILINE))
        await_count = txt.count("await ")
        print(f"async_check: defs={adef}, awaits={await_count}")
        if await_count > adef * 4:
            sys.stderr.write(
                "ASYNC_RATIO_SUSPICIOUS: more `await`s than expected; "
                "consider whether the function should be sync.\n"
            )
        return 0
    print("async_check: no async/await in file; skip")
    return 0


def cmd_f2p(args) -> int:
    test = Path(args.test)
    if not test.exists():
        sys.stderr.write(f"MISSING: {test}\n")
        return 2
    # Try docker first.
    if args.image and Path("/.dockerenv").exists() is False:
        proc = subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{Path.cwd()}:/app",
             "-w", "/app",
             args.image,
             "pytest", "-xvs", str(test)],
            capture_output=True, text=True, timeout=300,
        )
        if proc.returncode == 0:
            for ln in proc.stdout.splitlines():
                if "PASSED" in ln or "FAILED" in ln:
                    print(ln)
            if proc.returncode == 0:
                print("PASS")
                return 0
            print("FAIL")
            return 1
    # Fallback: local pytest.
    proc = subprocess.run(
        ["pytest", "-xvs", str(test)],
        capture_output=True, text=True, timeout=120,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode == 0:
        print("LOCAL_PASS (not F2P-grade; run via docker harness for verdict)")
        return 0
    print("FAIL")
    return 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("compile", help="py_compile one or more files.")
    pc.add_argument("--file", required=True, action="append",
                    help="Repeatable. File to py_compile.")

    pa = sub.add_parser("async-check", help="Extra sanity for async/await edits.")
    pa.add_argument("--file", required=True)

    pf = sub.add_parser("f2p", help="Run the f2p test.")
    pf.add_argument("--test", required=True)
    pf.add_argument("--image", default=None,
                    help="Optional docker image to use. Falls back to local pytest.")

    args = ap.parse_args()
    if args.cmd == "compile":
        sys.exit(cmd_compile(args))
    elif args.cmd == "async-check":
        sys.exit(cmd_async_check(args))
    elif args.cmd == "f2p":
        sys.exit(cmd_f2p(args))


if __name__ == "__main__":
    main()
