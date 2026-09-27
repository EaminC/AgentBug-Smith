#!/usr/bin/env python3
"""Score all rollouts in the pilot 20 set, save a summary CSV.

Iterates each (agent, skill_mode, issue) triple and runs the f2p judge
on the captured patch.txt. Aggregates outcomes into a single CSV.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--issues", type=Path, required=True)
    p.add_argument("--train-size", type=int, default=40)
    p.add_argument("--out", type=Path,
                   default=REPO_ROOT / "results" / "rq4" / "pilot_20_scores.csv")
    args = p.parse_args()

    rows = [json.loads(l) for l in args.issues.read_text().splitlines() if l.strip()]
    agents = ("mini-swe-agent", "openhands")
    skill_modes = ("with", "without")

    results = []
    for agent in agents:
        idx = REPO_ROOT / "data" / "verify" / f"issue_index_{agent}_{args.train_size}.jsonl"
        for skill in skill_modes:
            for r in rows:
                safe_repo = r["repo"].replace("/", "__")
                out_dir = (REPO_ROOT / "data" / "verify" / "runs"
                           / f"{agent}_{args.train_size}"
                           / f"{safe_repo}__{r['id']}"
                           / f"{skill}_skill")
                patch = out_dir / "patch.txt"
                eval_j = out_dir / "eval.json"
                agent_j = out_dir / "agent.json"
                # If eval.json missing but patch exists, score now.
                if not eval_j.exists() and patch.exists() and patch.stat().st_size > 0:
                    print(f"[score] {agent} {skill} {r['id']}", flush=True)
                    proc = subprocess.run(
                        ["python3", "-u",
                         "utils/verify/score.py", "score",
                         "--index", str(idx),
                         "--pilot-id", r["id"],
                         "--skill-mode", skill,
                         "--no-skip-done"],
                        cwd=REPO_ROOT, capture_output=True, text=True,
                    )
                # Record row.
                outcome = ""
                report_tail = ""
                if eval_j.exists():
                    try:
                        d = json.loads(eval_j.read_text())
                        outcome = d.get("outcome", "")
                        report_tail = (d.get("report_tail") or "")[:200]
                    except Exception:
                        pass
                has_patch = patch.exists() and patch.stat().st_size > 0
                has_agent_log = agent_j.exists()
                results.append({
                    "agent": agent,
                    "skill_mode": skill,
                    "issue": r["id"],
                    "repo": r["repo"],
                    "has_patch": has_patch,
                    "has_agent_log": has_agent_log,
                    "outcome": outcome,
                    "report_tail": report_tail,
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nWrote {args.out}")

    # Aggregate
    from collections import Counter
    by_combo = {}
    for r in results:
        key = (r["agent"], r["skill_mode"])
        by_combo.setdefault(key, Counter())[r["outcome"]] += 1
    print()
    print(f"{'agent':16s} {'skill':8s} {'total':>6s} {'f2p':>4s} {'f2f':>4s} {'p2p':>4s} {'p2f':>4s} {'err':>4s} {'pass@1':>7s}")
    for (agent, skill), c in sorted(by_combo.items()):
        n = sum(c.values())
        f2p = c.get("f2p", 0)
        f2f = c.get("f2f", 0)
        p2p = c.get("p2p", 0)
        p2f = c.get("p2f", 0)
        err = c.get("error", 0)
        print(f"{agent:16s} {skill:8s} {n:6d} {f2p:4d} {f2f:4d} {p2p:4d} {p2f:4d} {err:4d} {100*f2p/max(n,1):6.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
