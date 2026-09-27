#!/usr/bin/env python3
"""scan.py — run every capability scanner and print a ranked report.

This is the FIRST script the agent should run after localize.py.
It does not edit anything. Each hit is one JSON object with:

  capability, confidence, file, line, symbol, why, edit

Pick the highest-confidence hit that matches the failing assertion
and apply it with edit.py. Do not run more than one capability on
the same file until verify.py compile + f2p have been re-run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _lib import Hit, issue_blob
from boundary import scan as scan_boundary
from fallback_loop import scan as scan_fallback
from guard_empty import scan as scan_empty
from localize import localize
from plumb import scan as scan_plumb
from widen_match import scan as scan_widen


SCANNERS = (
    ("C_widen_match", scan_widen),
    ("C_normalize_empty", scan_empty),
    ("C_fallback_path", scan_fallback),
    ("C_boundary_zero", scan_boundary),
    ("C_plumb_arg", scan_plumb),
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--issue", type=Path, default=None)
    ap.add_argument("--test", type=Path, default=None)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()

    extra = args.test.read_text(errors="ignore") if args.test and args.test.exists() else ""
    blob = issue_blob(args.issue, extra)

    preferred: set[str] = set()
    if args.test and args.test.exists():
        try:
            for _sym, f, _ln in localize(args.test, args.src, blob):
                preferred.add(str(f).replace("\\", "/"))
        except Exception:
            preferred = set()

    hits: list[Hit] = []
    for name, fn in SCANNERS:
        try:
            hits.extend(fn(args.src, blob))
        except Exception as exc:  # noqa: BLE001 — scanners must not abort the rest
            print(json.dumps({"capability": name, "error": str(exc)}), file=sys.stderr)

    def _pref(h: Hit) -> int:
        fp = h.file.replace("\\", "/")
        return 0 if any(p in fp or fp.endswith(p) or fp in p for p in preferred) else 1

    rank = {"high": 0, "medium": 1, "low": 2}
    hits.sort(key=lambda h: (_pref(h), rank.get(h.confidence, 9), h.file, h.line))
    shown = hits[: args.top]
    if not shown:
        print("NO_HIT")
        sys.exit(2)

    # Human-readable header so the agent can pick a capability quickly.
    print("# capability scan")
    counts: dict[str, int] = {}
    for h in shown:
        counts[h.capability] = counts.get(h.capability, 0) + 1
    for cap, n in counts.items():
        print(f"#   {cap}: {n}")
    print("# ---")
    for h in shown:
        print(h.to_json())
    sys.exit(0)


if __name__ == "__main__":
    main()
