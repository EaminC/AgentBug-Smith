#!/usr/bin/env python3
"""Batch driver for the 80-rollout pilot.

Runs 20 issues x 2 agents x 2 skill modes = 80 rollouts.
Each (agent, skill_mode) is run sequentially because openhands and
mini-swe-agent both need exclusive use of the testbed clone at any
given time (they git checkout the base_sha each iteration).

Builds the docker image once per (issue), reusing it across both
skill modes. Per-issue concurrency is bounded by ``--workers`` (set
to 2 to balance docker build throughput vs LLM rate limits).

Usage:
    python utils/verify/run_pilot_20.py \
        --issues data/verify/pilot_20_issues.jsonl \
        --train-size 40 \
        --workers 2
"""

from __future__ import annotations

import argparse
import functools
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Force unbuffered stdout for live progress tracking.
print = functools.partial(print, flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--issues", type=Path, required=True,
                   help="JSONL with one row per pilot issue")
    p.add_argument("--train-size", type=int, default=40)
    p.add_argument("--workers", type=int, default=2,
                   help="Concurrent rollouts (each runs in its own subprocess)")
    p.add_argument("--cost-limit", type=float, default=3.0)
    p.add_argument("--skip-existing", action="store_true",
                   help="If patch.txt exists for a (agent,skill) combo, skip")
    p.add_argument("--out-summary", type=Path,
                  default=REPO_ROOT / "results" / "rq4" / "pilot_20_summary.json")
    args = p.parse_args()

    rows = [json.loads(l) for l in args.issues.read_text().splitlines() if l.strip()]
    print(f"loaded {len(rows)} pilot issues")

    agents = ("mini-swe-agent", "openhands")
    skill_modes = ("with", "without")
    todo = [(a, m, r) for a in agents for m in skill_modes for r in rows]

    # Simple worker pool: launch up to ``workers`` sub-processes
    import concurrent.futures
    completed = 0
    started_at = time.time()
    summary = []

    def run_one(agent: str, skill: str, row: dict) -> dict:
        idx_path = (REPO_ROOT / "data" / "verify" /
                    f"issue_index_{agent}_{args.train_size}.jsonl")
        cmd = [
            sys.executable, "-u", "utils/verify/solve.py", "rollout",
            "--index", str(idx_path),
            "--pilot-id", row["id"],
            "--skill-mode", skill,
            "--cost-limit", str(args.cost_limit),
        ]
        if not args.skip_existing:
            cmd.append("--no-skip-done")
        print(f"[start] {agent:14s} {skill:7s} {row['id']}")
        proc = subprocess.run(cmd, cwd=REPO_ROOT,
                              capture_output=True, text=True)
        out_tail = proc.stdout[-500:] if proc.stdout else ""
        err_tail = proc.stderr[-500:] if proc.stderr else ""
        print(f"[done ] {agent:14s} {skill:7s} {row['id']}  exit={proc.returncode}")
        if proc.returncode != 0:
            print(f"        stdout: {out_tail}")
            print(f"        stderr: {err_tail}")
        return {
            "agent": agent,
            "skill_mode": skill,
            "issue": row["id"],
            "repo": row.get("repo"),
            "exit_code": proc.returncode,
            "stdout_tail": out_tail,
            "stderr_tail": err_tail,
            "elapsed_s": time.time() - started_at,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(run_one, a, m, r) for a, m, r in todo]
        for f in concurrent.futures.as_completed(futs):
            try:
                r = f.result()
                summary.append(r)
                completed += 1
                elapsed = time.time() - started_at
                avg = elapsed / completed
                remaining = (len(todo) - completed) * avg
                print(f"[{completed}/{len(todo)}]  avg={avg:.0f}s/run  eta={remaining/60:.1f}min")
            except Exception as e:
                print(f"[ERROR] {e!r}")

    args.out_summary.parent.mkdir(parents=True, exist_ok=True)
    args.out_summary.write_text(json.dumps(summary, indent=2))
    print(f"\nDone. Summary: {args.out_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
