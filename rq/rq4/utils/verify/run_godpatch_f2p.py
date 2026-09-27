#!/usr/bin/env python3
"""Run f2p verify on a single issue using AgentSmith's run_f2p_verify.

Sets up the repo clone at base SHA, copies env.dockerfile + f2p test
from the verify pool, then runs run_f2p_verify which:
  1. docker build (before patch) → run test → expect fail
  2. git apply god-patch
  3. docker build (after patch)  → run test → expect pass

This verifies the **pipeline** (image build + test runner), independent
of the agent under test.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/home/anonymous/Desktop/RQ4")
AGENTSMITH_ROOT = Path("/home/anonymous/AgentBug-Smith")

sys.path.insert(0, str(AGENTSMITH_ROOT / "src"))
from testrun.verify import run_f2p_verify  # noqa: E402


def setup_repo(repo_dir: Path, base_sha: str, pool_dir: Path) -> None:
    """Reset repo to base_sha, install pool dockerfile + test."""
    subprocess.run(["git", "-C", str(repo_dir), "reset", "--hard", "HEAD"],
                   capture_output=True, text=True, check=False)
    subprocess.run(["git", "-C", str(repo_dir), "checkout", base_sha],
                   capture_output=True, text=True, check=False)
    subprocess.run(["git", "-C", str(repo_dir), "reset", "--hard", base_sha],
                   capture_output=True, text=True, check=False)

    df = pool_dir / "env.dockerfile"
    if df.exists():
        shutil.copy2(df, repo_dir / "env.dockerfile")

    src_test = next(pool_dir.glob("agentsmith_fail2pass_*.py"), None)
    if src_test:
        test_filename = src_test.name
        (repo_dir / "tests").mkdir(exist_ok=True)
        shutil.copy2(src_test, repo_dir / "tests" / test_filename)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--issue-id", required=True)
    ap.add_argument("--issue-json", required=True,
                    help="raw issue JSON (with linked_prs[0].patch + base_sha)")
    ap.add_argument("--test-relpath", required=False, default=None)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.index)]
    row = next((r for r in rows if r["id"] == args.issue_id), None)
    if not row:
        print(f"issue {args.issue_id} not in {args.index}", file=sys.stderr)
        return 2

    repo = row["repo"]
    base_sha = row["base_sha"]
    pool_dir = Path(row["verify_dir"])
    owner, name = repo.split("/", 1)
    repo_dir = AGENTSMITH_ROOT / "data" / f"{owner}_{name}"

    print(f"== setup: {repo} @ {base_sha[:10]} ==")
    setup_repo(repo_dir, base_sha, pool_dir)

    print("== run_f2p_verify (god-patch from linked_prs) ==")
    test_rel = args.test_relpath or row.get("test_relpath")
    outcome, report = run_f2p_verify(
        repo_root=repo_dir,
        issue_json_path=args.issue_json,
        dockerfile="env.dockerfile",
        test_relpath=test_rel,
        verbose=True,
    )
    print(f"\n== RESULT: outcome={outcome} ==\n")
    print(report[-6000:])
    return 0 if outcome == "f2p" else 1


if __name__ == "__main__":
    sys.exit(main())
