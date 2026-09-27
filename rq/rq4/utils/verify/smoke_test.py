#!/usr/bin/env python3
"""smoke_test.py — quick verification of the new agent code paths.

Runs ONE mini-swe-agent rollout via the new ``docker run`` path and
ONE openhands rollout via the new SDK path. Outputs to
``data/verify/runs/_smoke/``.

Usage:
    python utils/verify/smoke_test.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Make verify importable as a package.
ROOT = Path("/home/anonymous/Desktop/RQ4")
sys.path.insert(0, str(ROOT / "utils"))

# Load .env first.
for envfile in (ROOT / "agent" / "config" / ".env",
                ROOT / "agent" / "openhands-config" / ".env"):
    if envfile.exists():
        for ln in envfile.read_text().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Set AGENTSMITH_ROOT if not set
os.environ.setdefault("AGENTSMITH_ROOT", str(Path.home() / "AgentBug-Smith"))

from dataclasses import dataclass
from typing import Any

from verify.solve import (
    Row, RunSpec, spec_for_row,
    _run_mini_swe_agent_docker_run,
    _run_openhands_sdk,
    spec_is_done, build_one_image,
)


def load_rows():
    """Load one row each from mini-swe-agent_60 and openhands_40."""
    out = []
    for combo, idx_name in [
        ("mini-swe-agent_60", "issue_index_mini-swe-agent_60.jsonl"),
        ("openhands_40", "issue_index_openhands_40.jsonl"),
    ]:
        idx = ROOT / "data" / "verify" / idx_name
        for line in idx.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("split") == 1 and rec.get("id") == "issue-102" and "agentscope" in rec.get("repo", ""):
                rec["source_split"] = {"agent": combo.split("_")[0],
                                       "train_size_requested": int(combo.split("_")[1])}
                rec["index_path"] = str(idx)
                out.append((combo, Row(index_path=idx, line_no=0, raw=rec)))
                break
    return out


def make_spec(row, with_skill, combo):
    return spec_for_row(row, with_skill=with_skill)


def run_one_mini(spec, prompt):
    print(f"  >> running mini-swe-agent (docker run path) on {spec.row.repo}/{spec.row.id} with_skill={spec.with_skill}", flush=True)
    repo_dir = (Path(os.environ["AGENTSMITH_ROOT"]).expanduser() / "data"
                / spec.row.repo.replace("/", "_"))
    started = time.time()
    result = _run_mini_swe_agent_docker_run(
        spec, prompt,
        repo_dir=repo_dir,
        image_tag=spec.image_tag,
        model="openai/gpt-4.1-mini",
        cost_limit=0.20,  # smoke-test cost cap
        env={**os.environ},
    )
    elapsed = time.time() - started
    print(f"  >> exit={result['exit_code']} elapsed={elapsed:.1f}s", flush=True)
    print(f"  >> stdout tail:\n{result.get('stdout_tail','')[-600:]}", flush=True)
    print(f"  >> stderr tail:\n{result.get('stderr_tail','')[-600:]}", flush=True)
    patch = spec.out_dir / "patch.txt"
    if patch.exists():
        print(f"  >> patch.txt: {patch.stat().st_size} bytes", flush=True)
        print(f"  >> patch head: {patch.read_text()[:200]!r}", flush=True)
    else:
        print(f"  >> NO patch.txt produced", flush=True)
    traj = spec.out_dir / "trajectory.json"
    if traj.exists():
        print(f"  >> trajectory.json: {traj.stat().st_size} bytes", flush=True)
    return result


def run_one_openhands(spec, prompt):
    print(f"  >> running openhands SDK on {spec.row.repo}/{spec.row.id} with_skill={spec.with_skill}", flush=True)
    repo_dir = (Path(os.environ["AGENTSMITH_ROOT"]).expanduser() / "data"
                / spec.row.repo.replace("/", "_"))
    started = time.time()
    result = _run_openhands_sdk(
        spec, prompt,
        repo_dir=repo_dir,
        model="openai/gpt-4.1-mini",
        cost_limit=0.20,
        env={**os.environ},
    )
    elapsed = time.time() - started
    print(f"  >> exit={result['exit_code']} elapsed={elapsed:.1f}s", flush=True)
    patch = spec.out_dir / "patch.txt"
    if patch.exists():
        print(f"  >> patch.txt: {patch.stat().st_size} bytes", flush=True)
        print(f"  >> patch head: {patch.read_text()[:200]!r}", flush=True)
    else:
        print(f"  >> NO patch.txt produced", flush=True)
    traj = spec.out_dir / "trajectory.json"
    if traj.exists():
        print(f"  >> trajectory.json: {traj.stat().st_size} bytes", flush=True)
    return result


def main():
    rows = load_rows()
    for combo, row in rows:
        print(f"\n=== {combo} / {row.id} ===")
        spec = make_spec(row, with_skill=False, combo=combo)
        # Use smoke-test out dir so we don't clobber existing pilot_20 results
        spec.out_dir = (ROOT / "data" / "verify" / "runs" / "_smoke"
                        / combo / row.id / ("with_skill" if spec.with_skill else "without_skill"))
        spec.out_dir.mkdir(parents=True, exist_ok=True)

        # Build the docker image (skip if already exists).
        print(f"  >> building image {spec.image_tag}")
        ok, log = build_one_image(spec)
        if not ok:
            print(f"  >> BUILD FAILED: {log[:300]}")
            continue
        print(f"  >> build OK")

        # Use a trimmed prompt (just the issue body) to keep cost low.
        prompt = (
            "You are fixing a GitHub issue. The workspace is mounted at "
            "/testbed (or your container's cwd). Look at the issue below, "
            "make the minimal code change to fix it, and verify with "
            "the existing tests. Submit when done.\n\n"
            "Issue: agentscope-ai/agentscope#102 - Missing __init__.py for "
            "agentscope.web.studio directory.\n\n"
            "Note: This is a smoke test, so keep your solution minimal."
        )

        if "mini-swe-agent" in combo:
            run_one_mini(spec, prompt)
        else:
            run_one_openhands(spec, prompt)


if __name__ == "__main__":
    main()
