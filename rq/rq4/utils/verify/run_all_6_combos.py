#!/usr/bin/env python3
"""Driver: run all 6 (agent, scale) combos, then aggregate + plot.

Each combo: 20 issues × 2 skill modes × 2 agents = 80 rollouts.
Rollouts → score → aggregate → plot.

Usage:
    python utils/verify/run_all_6_combos.py
"""
from __future__ import annotations

import concurrent.futures
import csv
import functools
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MODES = ("with_skill", "without_skill")
COST_LIM = 3.0
WORKERS = 2

print = functools.partial(print, flush=True)

SCALES = [40, 60, 80]
AGENTS = ["mini-swe-agent", "openhands"]


def run_combo(agent: str, scale: int) -> tuple[int, str, int]:
    """Run 80 rollouts (20 issues × 2 skill modes) + score for one combo."""
    issues_file = REPO_ROOT / "data" / "verify" / f"pilot_20_issues_{agent}_{scale}.jsonl"
    index_file  = REPO_ROOT / "data" / "verify" / f"issue_index_{agent}_{scale}.jsonl"
    key = f"{agent}_{scale}"
    summary_out = REPO_ROOT / "results" / "rq4" / f"{key}_summary.json"
    scores_out  = REPO_ROOT / "results" / "rq4" / f"{key}_scores.csv"

    if not issues_file.exists():
        print(f"[{key}] SKIP: {issues_file} not found")
        return 0, key, scale

    # Rollouts
    print(f"\n{'='*60}\n>>> [{key}] Starting 80 rollouts\n{'='*60}")
    t0 = time.time()
    rc = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "run_pilot_20.py"),
        "--issues", str(issues_file),
        "--train-size", str(scale),
        "--workers", str(WORKERS),
        "--cost-limit", str(COST_LIM),
        "--out-summary", str(summary_out),
        "--skip-existing",
    ], cwd=REPO_ROOT).returncode
    print(f"[{key}] rollouts done in {(time.time()-t0)/60:.1f}min, rc={rc}")

    # Score
    print(f"[{key}] scoring")
    sr = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "score_all.py"),
        "--issues", str(issues_file),
        "--train-size", str(scale),
        "--out", str(scores_out),
    ], cwd=REPO_ROOT).returncode
    print(f"[{key}] scoring done, rc={sr}")

    return max(rc, sr), key, scale


def aggregate_and_plot():
    """Merge 6 per-combo CSVs into all_combos_scores.csv and plot."""
    out = REPO_ROOT / "results" / "rq4" / "all_combos_scores.csv"
    all_rows = []
    fieldnames = None

    for agent in AGENTS:
        for scale in SCALES:
            key = f"{agent}_{scale}"
            f = REPO_ROOT / "results" / "rq4" / f"{key}_scores.csv"
            if not f.exists():
                continue
            with f.open(newline="") as fh:
                reader = csv.DictReader(fh)
                fieldnames = reader.fieldnames
                for row in reader:
                    row["agent"] = agent
                    row["train_size"] = scale
                    all_rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    fields = (fieldnames or []) + ["agent", "train_size"]
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nAggregated {len(all_rows)} rows → {out}")

    # Print summary table
    print(f"\n{'='*70}")
    print(f"{'combo':22s} {'skill':10s} {'n':>4s} {'f2p':>4s} {'f2f':>4s} {'p2p':>4s} {'pass@1':>7s}")
    for agent in AGENTS:
        for scale in SCALES:
            key = f"{agent}_{scale}"
            grp = [r for r in all_rows if r["agent"] == agent and str(r.get("train_size")) == str(scale)]
            for skill in SKILL_MODES:
                sub = [r for r in grp if r.get("skill_mode") == skill]
                n = len(sub)
                f2p = sum(1 for r in sub if r.get("outcome") == "f2p")
                f2f = sum(1 for r in sub if r.get("outcome") == "f2f")
                p2p = sum(1 for r in sub if r.get("outcome") == "p2p")
                label = "with_skill" if "with" in skill else "no_skill"
                print(f"{key:22s} {label:10s} {n:4d} {f2p:4d} {f2f:4d} {p2p:4d} {100*f2p/max(n,1):6.1f}%")
    print(f"{'='*70}")

    # Plot
    print("\nPlotting...")
    pr = subprocess.run([
        sys.executable, "-u",
        str(REPO_ROOT / "utils" / "verify" / "plot_all_scales.py"),
        "--csv", str(out),
    ], cwd=REPO_ROOT)
    print(f"Plot done, rc={pr.returncode}")
    return out


def main() -> int:
    t0 = time.time()
    results = {}

    # Run all 6 combos in parallel (3 scales)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futs = {ex.submit(run_combo, agent, scale): (agent, scale)
                for agent in AGENTS for scale in SCALES}
        for f in concurrent.futures.as_completed(futs):
            agent, scale = futs[f]
            try:
                rc, key, s = f.result()
                results[key] = rc
                print(f"\n[thread {key}] finished, rc={rc}")
            except Exception as e:
                print(f"\n[thread {key}] ERROR: {e!r}")
                results[key] = 99

    total_time = time.time() - t0
    print(f"\nAll combos done in {total_time/60:.1f}min")
    for k, rc in results.items():
        print(f"  {k}: rc={rc}")

    csv_path = aggregate_and_plot()
    return max(results.values()) if results else 1


if __name__ == "__main__":
    sys.exit(main())
