#!/usr/bin/env python3
"""Run all 3 scales (40/60/80) in parallel, then aggregate + plot.

Usage:
    python utils/verify/run_all_scales.py
"""
from __future__ import annotations

import concurrent.futures
import csv
import functools
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ISSUES    = REPO_ROOT / "data" / "verify" / "pilot_20_issues_v2.jsonl"
SCALES    = [40, 60, 80]
WORKERS   = 2          # concurrent rollouts per scale
COST_LIM = 3.0

print = functools.partial(print, flush=True)


def run_scale(scale: int) -> tuple[int, str]:
    """Run all 80 rollouts for one scale. Returns (returncode, scale_name)."""
    name = f"scale{scale}"
    summary_out = REPO_ROOT / "results" / "rq4" / f"{name}_summary.json"
    scores_out   = REPO_ROOT / "results" / "rq4" / f"{name}_scores.csv"

    t0 = time.time()

    # ── 1. Rollouts ────────────────────────────────────────────────────────
    print(f"\n{'='*60}\n>>> Scale {scale}: starting {80} rollouts\n{'='*60}")
    rc = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "run_pilot_20.py"),
        "--issues", str(ISSUES),
        "--train-size", str(scale),
        "--workers", str(WORKERS),
        "--cost-limit", str(COST_LIM),
        "--out-summary", str(summary_out),
        "--skip-existing",
    ], cwd=REPO_ROOT).returncode

    elapsed = time.time() - t0
    print(f">>> Scale {scale}: rollouts done in {elapsed/60:.1f}min, rc={rc}")

    # ── 2. Score ────────────────────────────────────────────────────────────
    print(f">>> Scale {scale}: scoring")
    sr = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "score_all.py"),
        "--issues", str(ISSUES),
        "--train-size", str(scale),
        "--out", str(scores_out),
    ], cwd=REPO_ROOT).returncode
    print(f">>> Scale {scale}: scoring done, rc={sr}")

    return max(rc, sr), name


def aggregate():
    """Merge all per-scale CSVs into results/rq4/all_scales_scores.csv."""
    out = REPO_ROOT / "results" / "rq4" / "all_scales_scores.csv"
    all_rows = []
    fieldnames = None
    for scale in SCALES:
        f = REPO_ROOT / "results" / "rq4" / f"scale{scale}_scores.csv"
        if f.exists():
            with f.open(newline="") as fh:
                reader = csv.DictReader(fh)
                fieldnames = reader.fieldnames
                for row in reader:
                    row["train_size"] = scale
                    all_rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=(fieldnames or []) + ["train_size"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nAggregated {len(all_rows)} rows → {out}")

    # Print summary
    print(f"\n{'='*70}")
    print(f"{'scale':7s} {'agent':16s} {'skill':8s} {'n':>4s} "
          f"{'f2p':>4s} {'f2f':>4s} {'p2p':>4s} {'pass@1':>7s}")
    for scale in SCALES:
        scale_rows = [r for r in all_rows if int(r.get("train_size", 0)) == scale]
        for (agent, skill), grp in Counter(
                (r["agent"], r["skill_mode"]) for r in scale_rows).items():
            c = Counter(r["outcome"] for r in scale_rows
                        if r["agent"] == agent and r["skill_mode"] == skill)
            n = len([r for r in scale_rows
                     if r["agent"] == agent and r["skill_mode"] == skill])
            f2p = c.get("f2p", 0)
            f2f = c.get("f2f", 0)
            p2p = c.get("p2p", 0)
            print(f"scale{scale:3d} {agent:16s} {skill:8s} {n:4d} "
                  f"{f2p:4d} {f2f:4d} {p2p:4d} {100*f2p/max(n,1):6.1f}%")
    print(f"{'='*70}")
    return out


def main() -> int:
    t0 = time.time()

    # ── Run all 3 scales in parallel ────────────────────────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(run_scale, s): s for s in SCALES}
        results = {}
        for f in concurrent.futures.as_completed(futs):
            s = futs[f]
            try:
                rc, name = f.result()
                results[s] = rc
                print(f"\n[thread scale={s}] finished, rc={rc}")
            except Exception as e:
                print(f"\n[thread scale={s}] ERROR: {e!r}")
                results[s] = 99

    total_time = time.time() - t0
    print(f"\nAll scales done in {total_time/60:.1f}min")
    for s, rc in results.items():
        print(f"  scale{s}: rc={rc}")

    # ── Aggregate ─────────────────────────────────────────────────────────
    csv_path = aggregate()

    # ── Plot ──────────────────────────────────────────────────────────────
    print("\nPlotting...")
    pr = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "plot_all_scales.py"),
        "--csv", str(csv_path),
    ], cwd=REPO_ROOT)
    print(f"Plot done, rc={pr.returncode}")

    return max(results.values()) if results else 1


if __name__ == "__main__":
    sys.exit(main())
