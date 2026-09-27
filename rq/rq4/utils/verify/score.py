#!/usr/bin/env python3
"""score.py — Component 7: f2p judge.

For each captured rollout artifact (one issue × one skill_mode), apply
the agent's ``patch.txt`` on top of the base HEAD and re-run the
verify-pool's ``agentsmith_fail2pass_<NNN>.py`` test inside the same
Docker image built during rollout. Classify the outcome as
``f2p | f2f | p2p | p2f | error`` per
``AgentBug-Smith/src/testrun/verify.py::run_f2p_verify``.

The point of the rollout phase is to produce a *candidate* patch from
the agent. ``run_f2p_verify`` as upstreamed reads the patch from the
issue JSON's ``linked_prs[0].patch`` (the gold patch). We can't reuse
that directly — we need to apply the agent's patch instead. The
helper reads ``ctx.patch`` exactly once via
``load_issue_testgen_context``, so the cleanest swap is:

    1. Load the verify pool's ``issue.json``.
    2. Inject the agent's patch text into ``linked_prs[0].patch``.
    3. Write a *temporary* issue JSON inside the rollout dir.
    4. Call ``run_f2p_verify(repo_root, tmp_json, test_relpath=...)``.

The tmp JSON is cleaned up after scoring. We then record
``{outcome, report_path, scored_at}`` into the rollout dir's
``eval.json`` and a flat ``results/eval/<key>.jsonl`` for downstream
aggregation.

Output
------
For every ``(key, id, skill_mode)`` rollout we add
``<artifacts_dir>/<key>/<repo>__<id>/{with,without}_skill/eval.json``
with::

    {
      "outcome":         "f2p" | "f2f" | "p2p" | "p2f" | "error",
      "report_path":     "<artifacts_dir>/.../eval_report.txt",
      "scored_at":       "2026-09-06T20:55:12.345+00:00",
      "agent":           "mini-swe-agent" | "openhands",
      "train_size":      40 | 60 | 80,
      "issue_id":        "issue-1058",
      "repo":            "agentscope-ai/agentscope",
      "skill_mode":      "with" | "without",
      "patch_source":    "<artifacts_dir>/.../patch.txt",
      "report_tail":     "outcome=f2p (rc1=1, rc2=0)\\n..."
    }

Usage
-----
::

    # Score everything that has a patch.txt (idempotent: skips ones with eval.json)
    python score.py --index data/verify/issue_index_mini-swe-agent_40.jsonl

    # Pilot a single issue
    python score.py \\
        --index data/verify/issue_index_mini-swe-agent_40.jsonl \\
        --pilot-id issue-1058

CLI
---
``score.py score``
    Run f2p judge for all rows in an index file.

``score.py summary``
    Aggregate per-(key, skill_mode) pass@1 from the eval.json files.

``score.py inspect``
    Print eval.json for one (id, skill_mode) combination.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "utils"))
sys.path.insert(0, str(Path.home() / "AgentBug-Smith" / "src"))

# Reuse the row loader and agent_repo_path from solve.py so the two
# stay in lockstep on what a "row" looks like and where the repo clone
# lives.
from verify.solve import load_rows, agent_repo_path, RUNS_ROOT  # noqa: E402

# Import AgentSmith's live verifier + helpers.
from testrun.verify import (  # noqa: E402
    run_f2p_verify,
    dockerbuild,
    _docker_image_tag,
    _docker_run,
    _classify,
)
from testgen.main import load_issue_testgen_context  # noqa: E402
from repo.git_ops import git_apply_patch, reset_repo_to_base  # noqa: E402

EVAL_ROOT = REPO_ROOT / "results" / "eval"
EVAL_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Per-rollout scoring
# ---------------------------------------------------------------------------

def _inject_patch(issue_json: Path, patch_text: str,
                  *, base_sha: str | None = None) -> Path:
    """Write a temporary issue JSON with ``linked_prs[0].patch`` swapped.

    Optionally also inject ``base_sha`` (when the source JSON lacks
    one — the pool we generate from AgentSmith sometimes drops it).

    Returns the tmp JSON path (caller must ``.unlink()``).
    """
    data = json.loads(issue_json.read_text(encoding="utf-8"))
    if not data.get("linked_prs"):
        data["linked_prs"] = [{}]
    data["linked_prs"][0]["patch"] = patch_text
    if base_sha:
        data["linked_prs"][0]["base_sha"] = base_sha
    tmp_path = issue_json.with_suffix(".patch_injected.json")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return tmp_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_one(
    artifacts_dir: Path,
    *,
    repo_root: Path,
    issue_json_src: Path,
    test_relpath: str | None,
    skill_mode: str,
    agent: str,
    train_size: int,
    issue_id: str,
    repo: str,
    row_base_sha: str | None = None,
) -> dict[str, Any]:
    """Score a single artifact directory's ``patch.txt``.

    ``artifacts_dir`` is the ``<key>/<repo>__<id>/{with,without}_skill``
    directory produced by rollout.
    """
    eval_path = artifacts_dir / "eval.json"
    if eval_path.exists():
        return json.loads(eval_path.read_text())

    patch_path = artifacts_dir / "patch.txt"
    agent_log  = artifacts_dir / "agent.json"
    if not patch_path.exists() or patch_path.stat().st_size == 0:
        record = {
            "outcome": "error",
            "error": "patch.txt missing or empty",
            "scored_at": _now(),
            "agent": agent, "train_size": train_size,
            "issue_id": issue_id, "repo": repo, "skill_mode": skill_mode,
        }
        eval_path.write_text(json.dumps(record, indent=2))
        return record

    patch_text = patch_path.read_text(encoding="utf-8")
    # Resolve base_sha up-front (issue JSON may lack it; fall back to
    # row.base_sha). Inject it into the tmp JSON so AgentSmith's
    # ``run_f2p_verify`` can use it for the reset step too.
    ctx_probe = load_issue_testgen_context(issue_json_src)
    effective_base_sha = ctx_probe.base_sha or row_base_sha
    tmp_json = _inject_patch(issue_json_src, patch_text,
                             base_sha=effective_base_sha)
    try:
        # Reset the repo to base HEAD, then drop the agent's earlier
        # generated files (env.dockerfile + test) before delegating to
        # the upstream verifier.
        if not effective_base_sha:
            record = {
                "outcome": "error",
                "error": "no base_sha in issue JSON or row",
                "scored_at": _now(),
                "agent": agent, "train_size": train_size,
                "issue_id": issue_id, "repo": repo, "skill_mode": skill_mode,
            }
            eval_path.write_text(json.dumps(record, indent=2))
            return record

        ok_reset, reset_log = reset_repo_to_base(repo_root, effective_base_sha)
        if not ok_reset:
            record = {
                "outcome": "error",
                "error": f"reset_repo_to_base failed: {reset_log}",
                "scored_at": _now(),
                "agent": agent, "train_size": train_size,
                "issue_id": issue_id, "repo": repo, "skill_mode": skill_mode,
            }
            eval_path.write_text(json.dumps(record, indent=2))
            return record

        outcome, report = run_f2p_verify(
            repo_root=repo_root,
            issue_json_path=tmp_json,
            test_relpath=test_relpath,
            verbose=False,
        )

        report_path = artifacts_dir / "eval_report.txt"
        report_path.write_text(report, encoding="utf-8")

        record = {
            "outcome": outcome,
            "report_path": str(report_path.relative_to(REPO_ROOT)),
            "scored_at": _now(),
            "agent": agent,
            "train_size": train_size,
            "issue_id": issue_id,
            "repo": repo,
            "skill_mode": skill_mode,
            "patch_source": str(patch_path.relative_to(REPO_ROOT)),
            "report_tail": report[-1500:],
            "cost_to_score_seconds": time.time(),
        }
    except Exception as e:
        record = {
            "outcome": "error",
            "error": repr(e),
            "scored_at": _now(),
            "agent": agent, "train_size": train_size,
            "issue_id": issue_id, "repo": repo, "skill_mode": skill_mode,
        }
    finally:
        try:
            tmp_json.unlink()
        except FileNotFoundError:
            pass

    eval_path.write_text(json.dumps(record, indent=2))
    return record


# ---------------------------------------------------------------------------
# Iterators
# ---------------------------------------------------------------------------

def iter_artifacts(index_path: Path, *,
                   skill_modes: list[str],
                   pilot_id: str | None = None) -> Iterable[dict[str, Any]]:
    """Yield one record per (id, skill_mode) on the index."""
    rows = load_rows(index_path, only_test=True)
    for row in rows:
        if pilot_id and row.id != pilot_id:
            continue
        ss = row.raw.get("source_split", {})
        agent = ss.get("agent") or "mini-swe-agent"
        train_size = int(ss.get("train_size_requested") or 0)
        key = f"{agent}_{train_size}"
        safe_repo = row.repo.replace("/", "__")
        for sm in skill_modes:
            artifacts_dir = RUNS_ROOT / key / f"{safe_repo}__{row.id}" / sm
            yield {
                "artifacts_dir": artifacts_dir,
                "issue_json_src": row.verify_dir / "issue.json",
                "test_relpath": row.test_relpath,
                "skill_mode": sm,
                "agent": agent,
                "train_size": train_size,
                "issue_id": row.id,
                "repo": row.repo,
                "row": row,
            }


def cmd_score(index_path: Path, *,
              skill_modes: list[str],
              pilot_id: str | None = None,
              skip_done: bool = True) -> dict[str, int]:
    stats = {"score": 0, "skipped": 0, "error": 0, "f2p": 0, "f2f": 0,
             "p2p": 0, "p2f": 0}
    for spec in iter_artifacts(index_path, skill_modes=skill_modes, pilot_id=pilot_id):
        adir = spec["artifacts_dir"]
        eval_path = adir / "eval.json"
        if skip_done and eval_path.exists():
            prev = json.loads(eval_path.read_text())
            stats["skipped"] += 1
            counts_tally(stats, prev["outcome"])
            print(f"  · {spec['issue_id']} / {spec['skill_mode']:7s}  SKIP  outcome={prev['outcome']}")
            continue
        if not (adir / "patch.txt").exists():
            stats["error"] += 1
            print(f"  · {spec['issue_id']} / {spec['skill_mode']:7s}  NO patch.txt — skipped")
            continue
        try:
            repo_root = agent_repo_path(spec["repo"])
            record = _score_one(
                adir,
                repo_root=repo_root,
                issue_json_src=spec["issue_json_src"],
                test_relpath=spec["test_relpath"],
                skill_mode=spec["skill_mode"],
                agent=spec["agent"],
                train_size=spec["train_size"],
                issue_id=spec["issue_id"],
                repo=spec["repo"],
                row_base_sha=spec["row"].base_sha,
            )
        except Exception as e:
            stats["error"] += 1
            print(f"  · {spec['issue_id']} / {spec['skill_mode']:7s}  ERROR  {e!r}")
            continue
        stats["score"] += 1
        counts_tally(stats, record["outcome"])
        print(f"  · {spec['issue_id']} / {spec['skill_mode']:7s}  outcome={record['outcome']}")
    return stats


def counts_tally(stats: dict[str, int], outcome: str) -> None:
    if outcome in ("f2p", "f2f", "p2p", "p2f"):
        stats[outcome] += 1
    elif outcome == "error":
        stats["error"] += 1


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="f2p judge for rollout artifacts.")
    sub = p.add_subparsers(dest="mode", required=True)

    sc = sub.add_parser("score", help="Run f2p judge over an index file.")
    sc.add_argument("--index", type=Path, required=True)
    sc.add_argument("--pilot-id", type=str, default=None)
    sc.add_argument("--skill-mode",
                    choices=["with", "without", "all"], default="all")
    sc.add_argument("--no-skip-done", action="store_true")

    sm = sub.add_parser("summary",
                        help="Aggregate per-(key, skill_mode) pass@1.")
    sm.add_argument("--index", type=Path, required=True)

    ins = sub.add_parser("inspect", help="Print eval.json for one (id, skill_mode).")
    ins.add_argument("--index", type=Path, required=True)
    ins.add_argument("--pilot-id", type=str, required=True)
    ins.add_argument("--skill-mode",
                     choices=["with", "without", "all"], default="all")

    args = p.parse_args()

    if args.mode == "score":
        sm = ["with_skill", "without_skill"] if args.skill_mode == "all" \
             else [f"{args.skill_mode}_skill"]
        stats = cmd_score(args.index, skill_modes=sm,
                          pilot_id=args.pilot_id,
                          skip_done=not args.no_skip_done)
        print(json.dumps(stats, indent=2))
        return 0

    if args.mode == "summary":
        # Aggregate over eval.json files written by ``score``.
        rows = load_rows(args.index, only_test=True)
        bins: dict[tuple[str, str], dict[str, int]] = {}
        for row in rows:
            ss = row.raw.get("source_split", {})
            agent = ss.get("agent") or "mini-swe-agent"
            train_size = int(ss.get("train_size_requested") or 0)
            key = f"{agent}_{train_size}"
            for skill_mode in ("with_skill", "without_skill"):
                p = RUNS_ROOT / key / f"{row.repo.replace('/', '__')}__{row.id}" / skill_mode / "eval.json"
                if not p.exists():
                    continue
                bin_ = bins.setdefault((key, skill_mode),
                                       {"n": 0, "f2p": 0, "f2f": 0, "p2p": 0,
                                        "p2f": 0, "error": 0})
                rec = json.loads(p.read_text())
                bin_["n"] += 1
                outcome = rec.get("outcome", "error")
                if outcome in bin_:
                    bin_[outcome] += 1
                else:
                    bin_["error"] += 1
        print(f"{'key':<28} {'skill_mode':<14} {'n':>4} {'f2p':>5} {'f2f':>5} {'p2p':>5} {'p2f':>5} {'err':>5}  {'pass@1':>8}")
        for (key, skill_mode), b in sorted(bins.items()):
            pass_at_1 = (b["f2p"] / b["n"] * 100.0) if b["n"] else 0.0
            print(f"{key:<28} {skill_mode:<14} {b['n']:>4} {b['f2p']:>5} {b['f2f']:>5} {b['p2p']:>5} {b['p2f']:>5} {b['error']:>5}  {pass_at_1:>7.1f}%")
        return 0

    if args.mode == "inspect":
        skill_modes = ["with_skill", "without_skill"] if args.skill_mode == "all" \
                      else [f"{args.skill_mode}_skill"]
        for spec in iter_artifacts(args.index,
                                   skill_modes=skill_modes,
                                   pilot_id=args.pilot_id):
            eval_path = spec["artifacts_dir"] / "eval.json"
            print(f"\n--- {spec['issue_id']} / {spec['skill_mode']} ---")
            if not eval_path.exists():
                print("(no eval.json yet)")
                continue
            print(eval_path.read_text())
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
