#!/usr/bin/env python3
"""reextract_patches.py — re-extract patches from existing rollout
artifacts using updated exclude patterns.

For each rollout:
  1. Reset the workspace repo to the base SHA
  2. Apply the rollout's agent.json trajectory's last diff (best effort)
  3. Run the new git diff with updated exclusions
  4. Save to patch.txt

This avoids re-running the (expensive) agent and instead re-derives
the patch from the workspace's final state.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path("/home/anonymous/Desktop/RQ4")
AGENTSMITH_ROOT = Path("/home/anonymous/AgentBug-Smith")

COMBOS = [
    "mini-swe-agent_40", "mini-swe-agent_60", "mini-swe-agent_80",
    "openhands_40", "openhands_60", "openhands_80",
]

EXCLUDE_ARGS = [
    ":!env.dockerfile",
    ":!tests/agentsmith_*",
    ":!*.db", ":!*.sqlite", ":!*.sqlite3",
    ":!patch.txt",
    ":!*.log",
    ":!test_runs",
    ":!.config",
    ":!repro*.py", ":!reproduce*.py",
    ":!scratch*.py",
    ":!test_repro*.py",
    ":!patch_*.py",
    ":!debug_*.py",
    ":!tmp_*.py",
    ":!result.log",
    ":!verify_*.py",
    ":!check_*.py",
]


def agent_repo_dir(repo: str) -> Path:
    owner, name = repo.split("/", 1)
    return AGENTSMITH_ROOT / "data" / f"{owner}_{name}"


def get_base_sha(combo: str, issue_id: str) -> str:
    idx = REPO_ROOT / f"data/verify/issue_index_pilot30_{combo}.jsonl"
    for line in idx.read_text().splitlines():
        d = json.loads(line)
        if d["id"] == issue_id:
            return d.get("base_sha", "")
    return ""


def reextract_patch(combo: str, issue_id: str) -> int:
    """Re-extract patches for one (combo, issue). Returns count re-extracted."""
    idx = REPO_ROOT / f"data/verify/issue_index_pilot30_{combo}.jsonl"
    meta = None
    for line in idx.read_text().splitlines():
        d = json.loads(line)
        if d["id"] == issue_id:
            meta = d
            break
    if not meta:
        return 0

    repo = meta["repo"]
    base_sha = meta["base_sha"]
    repo_dir = agent_repo_dir(repo)

    run_dir = REPO_ROOT / f"data/verify/runs/{combo}/{repo.replace('/', '__')}__{issue_id}"
    if not run_dir.exists():
        return 0

    # Check if there's something to re-extract from
    n_done = 0
    for skill in ["with_skill", "without_skill"]:
        skill_dir = run_dir / skill
        if not skill_dir.exists():
            continue

        # Reset repo to base SHA + apply agent's last diff
        # But we can't redo the agent — instead just re-run git diff
        # with new exclusions on whatever's in the workspace

        # Reset to base SHA
        subprocess.run(["git", "-C", str(repo_dir), "reset", "--hard", "HEAD"],
                       capture_output=True, check=False)
        r = subprocess.run(["git", "-C", str(repo_dir), "checkout", base_sha],
                          capture_output=True, check=False)
        r = subprocess.run(["git", "-C", str(repo_dir), "reset", "--hard", base_sha],
                          capture_output=True, check=False)
        subprocess.run(["git", "-C", str(repo_dir), "clean", "-fd"],
                       capture_output=True, check=False)

        # If there's an old patch.txt, try to re-apply it then re-diff
        old_patch = skill_dir / "patch.txt"
        if old_patch.exists():
            patch_text = old_patch.read_text()
            # Filter out scratch file hunks
            keep_lines = []
            skip_file = None
            for line in patch_text.splitlines():
                if line.startswith("diff --git "):
                    # Parse filename
                    fname = line.split(" b/", 1)[-1]
                    # Check if filename should be excluded
                    skip = False
                    for pattern in ["repro", "reproduce", "scratch",
                                    "test_repro", "patch_openai",
                                    "debug_", "tmp_", "result.log",
                                    "verify_", "check_"]:
                        if pattern in fname.lower():
                            skip = True
                            break
                    skip_file = fname if skip else None
                    if not skip:
                        keep_lines.append(line)
                elif skip_file is not None:
                    # Skip lines belonging to this file (next/header/body until next diff)
                    if line.startswith("diff --git "):
                        # Process new diff header
                        fname = line.split(" b/", 1)[-1]
                        skip = False
                        for pattern in ["repro", "reproduce", "scratch",
                                        "test_repro", "patch_openai",
                                        "debug_", "tmp_", "result.log",
                                        "verify_", "check_"]:
                            if pattern in fname.lower():
                                skip = True
                                break
                        skip_file = fname if skip else None
                        if not skip:
                            keep_lines.append(line)
                else:
                    keep_lines.append(line)

            new_patch = "\n".join(keep_lines) + "\n"
            skill_dir.mkdir(exist_ok=True)
            skill_dir.joinpath("patch.txt").write_text(new_patch)
            n_done += 1

    return n_done


def main():
    PILOT30 = ["issue-1208", "issue-1351", "issue-1689", "issue-3493", "issue-1528"]
    total = 0
    for combo in COMBOS:
        for issue in PILOT30:
            n = reextract_patch(combo, issue)
            total += n
            if n:
                print(f"  {combo} {issue}: re-extracted {n} patches")
    print(f"\nTotal: {total} patches re-extracted")


if __name__ == "__main__":
    main()
