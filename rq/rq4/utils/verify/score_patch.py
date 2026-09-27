#!/usr/bin/env python3
"""Score an agent's patch.txt via AgentSmith's run_f2p_verify.

Usage:
    python3 utils/verify/score_patch.py \
        --index <index.jsonl> --issue-id <id> \
        --patch-file <patch.txt> \
        [--issue-json <raw issue JSON with linked_prs[0].patch>]

Pipeline:
  1. Reset repo to base_sha, install pool dockerfile + test.
  2. Build image, run test → expect fail.
  3. Apply agent's patch.
  4. Rebuild, run test → expect pass.
  5. Reset repo, repeat with god-patch (sanity check).
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
from dockerbuild.build import dockerbuild  # noqa: E402
from repo.git_ops import git_apply_patch  # noqa: E402
from testrun.verify import _docker_run, _docker_image_tag, _last_workdir_in_dockerfile  # noqa: E402


def setup_repo(repo_dir: Path, base_sha: str, pool_dir: Path) -> None:
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
        (repo_dir / "tests").mkdir(exist_ok=True)
        shutil.copy2(src_test, repo_dir / "tests" / src_test.name)


def run_one_f2p(repo_dir: Path, patch_text: str, test_relpath: str) -> tuple[str, str]:
    """Apply patch_text, build image, run test. Return (rc, output)."""
    ok_a, log_a = dockerbuild(repo_dir, dockerfile="env.dockerfile",
                              project_root=AGENTSMITH_ROOT, verbose=False)
    if not ok_a:
        return ("error", log_a[-3000:])
    image_tag = _docker_image_tag(repo_dir)
    wd = _last_workdir_in_dockerfile(repo_dir / "env.dockerfile")
    rc, out = _docker_run(repo_dir, image_tag,
                          ["python", "-m", "pytest", "-q", test_relpath],
                          workdir=wd)
    return (str(rc), out[-3000:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--issue-id", required=True)
    ap.add_argument("--patch-file", required=True,
                    help="path to agent patch (unified diff)")
    ap.add_argument("--issue-json", required=True,
                    help="raw issue JSON (linked_prs[0].patch is the god-patch)")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.index)]
    row = next((r for r in rows if r["id"] == args.issue_id), None)
    if not row:
        print(f"issue {args.issue_id} not in {args.index}", file=sys.stderr)
        return 2

    repo = row["repo"]
    base_sha = row["base_sha"]
    pool_dir = Path(row["verify_dir"])
    test_relpath = row["test_relpath"]
    owner, name = repo.split("/", 1)
    repo_dir = AGENTSMITH_ROOT / "data" / f"{owner}_{name}"

    print(f"== scoring agent patch for {args.issue_id} on {repo} ==", flush=True)
    setup_repo(repo_dir, base_sha, pool_dir)

    # Phase 1: agent patch
    print("== applying agent patch ==", flush=True)
    gok, gerr = git_apply_patch(repo_dir, Path(args.patch_file).read_text())
    if not gok:
        print(f"!! agent patch did not apply: {gerr}")
        return 1
    rc_agent, out_agent = run_one_f2p(repo_dir, Path(args.patch_file).read_text(),
                                      test_relpath)
    print(f"== agent patch: pytest exit={rc_agent} ==", flush=True)

    # Reset and run god-patch
    print("\n== reset, then sanity-check with god-patch ==", flush=True)
    setup_repo(repo_dir, base_sha, pool_dir)
    issue_data = json.load(open(args.issue_json))
    god_patch = (issue_data.get("linked_prs") or [{}])[0].get("patch", "")
    if not god_patch.strip():
        print("!! no god-patch in linked_prs[0].patch")
    else:
        gok2, gerr2 = git_apply_patch(repo_dir, god_patch)
        if not gok2:
            print(f"!! god-patch did not apply: {gerr2}")
        else:
            rc_god, out_god = run_one_f2p(repo_dir, god_patch, test_relpath)
            print(f"== god-patch: pytest exit={rc_god} ==", flush=True)
            if rc_god == "0":
                print(f"\n*** Pipeline is OK: god-patch passes (exit 0) ***")
            else:
                print(f"\n!!! Pipeline is BROKEN: god-patch failed (exit {rc_god}) !!!")

    print(f"\n=== agent pytest tail ===\n{out_agent[-1500:]}")
    return 0 if rc_agent == "0" else 1


if __name__ == "__main__":
    sys.exit(main())
