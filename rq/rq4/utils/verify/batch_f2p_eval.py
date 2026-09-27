#!/usr/bin/env python3
"""batch_f2p_eval.py — batch f2p evaluation for pilot30.

For each rollout artifact (patch.txt):
  1. Reset repo to base SHA
  2. Copy dockerfile + test
  3. Build base image
  4. Run test (expect fail for f2p test)
  5. Apply patch
  6. Rebuild image (pip install now gets patched code)
  7. Run test (expect pass)
  8. Record outcome

Writes results to results/rq4/pilot30_scores.csv
"""
import argparse, csv, json, os, shutil, subprocess, sys, time
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path("/home/anonymous/Desktop/RQ4")
AGENTSMITH_ROOT = Path("/home/anonymous/AgentBug-Smith")

sys.path.insert(0, str(AGENTSMITH_ROOT / "src"))
from testrun.verify import run_f2p_verify

COMBOS = [
    "mini-swe-agent_40", "mini-swe-agent_60", "mini-swe-agent_80",
    "openhands_40", "openhands_60", "openhands_80",
]
PILOT30_IDS = ["issue-1208", "issue-1351", "issue-1689", "issue-3493", "issue-1528"]
SKILL_MODES = ["with_skill", "without_skill"]


def get_index_info(issue_id: str, combo: str) -> tuple[str, str, str]:
    """Return (base_sha, repo, test_relpath) from the pilot30 index file."""
    idx_path = REPO_ROOT / f"data/verify/issue_index_pilot30_{combo}.jsonl"
    if not idx_path.exists():
        return "", "", ""
    for line in idx_path.read_text().splitlines():
        d = json.loads(line)
        if d.get("id") == issue_id:
            return (
                d.get("base_sha", ""),
                d.get("repo", ""),
                d.get("test_relpath", ""),
            )
    return "", "", ""


def agent_repo_dir(repo: str) -> Path:
    """Map repo name to AgentBug-Smith data directory."""
    owner, name = repo.split("/", 1)
    return AGENTSMITH_ROOT / "data" / f"{owner}_{name}"


def _run_f2p(specimen_tag: str, tmp_repo: Path,
              patch_text: str, test_relpath: str) -> tuple[int, str]:
    """Run pytest in container. Returns (exit_code, output_tail)."""
    env_line = f"source {REPO_ROOT / 'agent/config/.env'} && "
    cmd = [
        "docker", "run", "--rm", "--network=none",
        "-v", f"{REPO_ROOT / 'agent/config/.env'}:/env.env:ro",
        specimen_tag,
        "bash", "-c",
        f"pip install --quiet opentelemetry-sdk mcp opentelemetry-instrumentation-threading watchdog 2>/dev/null; "
        f"python -m pytest {test_relpath} -v --tb=short 2>&1",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def eval_one(patch_path: Path, combo: str,
             issue_id: str, skill_mode: str) -> dict:
    """Evaluate one patch. Returns result dict."""
    # Resolve paths
    repo_name = None
    base_sha = None
    test_relpath = None
    for line in (REPO_ROOT / f"data/verify/issue_index_pilot30_{combo}.jsonl").read_text().splitlines():
        d = json.loads(line)
        if d.get("id") == issue_id:
            base_sha = d.get("base_sha", "")
            repo_name = d.get("repo", "")
            test_relpath = d.get("test_relpath", "")
            break

    if not repo_name or not base_sha:
        return {"outcome": "error", "reason": "missing metadata"}

    repo = agent_repo_dir(repo_name)
    pool_dir = REPO_ROOT / f"data/verify/_pool/{repo_name.replace('/', '__')}__{issue_id}"
    issue_json = pool_dir / "issue.json"
    dockerfile = pool_dir / "env.dockerfile"

    if not repo.exists():
        return {"outcome": "error", "reason": f"repo not found: {repo}"}
    if not dockerfile.exists():
        return {"outcome": "error", "reason": f"dockerfile not found: {dockerfile}"}

    # Prepare working dir (clone of repo at base SHA)
    ts = int(time.time() * 1000)
    tmp_repo = Path(f"/tmp/f2p_{ts}")
    if tmp_repo.exists():
        shutil.rmtree(tmp_repo)
    shutil.copytree(repo, tmp_repo)
    subprocess.run(["git", "-C", str(tmp_repo), "checkout", base_sha],
                   capture_output=True, check=False)
    subprocess.run(["git", "-C", str(tmp_repo), "reset", "--hard", base_sha],
                   capture_output=True, check=False)

    # Copy dockerfile + test
    shutil.copy2(dockerfile, tmp_repo / "env.dockerfile")
    if test_relpath:
        test_src = pool_dir / test_relpath.split("/")[-1]
        if test_src.exists():
            test_dir = tmp_repo / "/".join(test_relpath.split("/")[:-1])
            test_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(test_src, tmp_repo / test_relpath)

    # Inject patch into issue.json for run_f2p_verify
    if issue_json.exists():
        issue = json.loads(issue_json.read_text())
        issue["linked_prs"] = [{"patch": patch_path.read_text()}]
        tmp_issue = tmp_repo / "_tmp_issue.json"
        tmp_issue.write_text(json.dumps(issue))
    else:
        tmp_issue = None

    # Run f2p verify
    try:
        if tmp_issue and tmp_issue.exists():
            outcome, report = run_f2p_verify(
                repo_root=str(tmp_repo),
                issue_json_path=str(tmp_issue),
                dockerfile="env.dockerfile",
                test_relpath=test_relpath or None,
                verbose=False,
            )
        else:
            outcome = "error"
            report = "issue.json not found"
    except Exception as e:
        outcome = "error"
        report = str(e)[:500]
    finally:
        if tmp_issue and tmp_issue.exists():
            tmp_issue.unlink()
        shutil.rmtree(tmp_repo)

    return {"outcome": outcome, "report": report[-1000:]}


def main():
    results = []
    for combo in COMBOS:
        run_base = REPO_ROOT / f"data/verify/runs/{combo}"
        if not run_base.exists():
            continue

        for issue_id in PILOT30_IDS:
            # Find the run dir (has repo__id format)
            matching = list(run_base.glob(f"*__{issue_id}"))
            if not matching:
                continue
            run_dir = matching[0]

            for skill_mode in SKILL_MODES:
                patch_path = run_dir / skill_mode / "patch.txt"
                if not patch_path.exists():
                    results.append({
                        "agent": combo.split("_")[0],
                        "train_size": combo.split("_")[1],
                        "skill_mode": skill_mode.replace("_", " "),
                        "issue": issue_id,
                        "has_patch": "False",
                        "outcome": "",
                        "report": "no patch",
                    })
                    continue

                print(f"  Evaluating {combo}/{issue_id}/{skill_mode}...", flush=True)
                res = eval_one(patch_path, combo, issue_id, skill_mode)
                results.append({
                    "agent": combo.split("_")[0],
                    "train_size": combo.split("_")[1],
                    "skill_mode": skill_mode.replace("_", " "),
                    "issue": issue_id,
                    "has_patch": "True",
                    "outcome": res.get("outcome", "error"),
                    "report": res.get("report", "")[:500],
                })

    # Write CSV
    out_path = REPO_ROOT / "results/rq4/pilot30_scores.csv"
    if results:
        fieldnames = ["agent", "train_size", "skill_mode", "issue",
                      "has_patch", "outcome", "report"]
        with open(out_path, "w") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(results)
        print(f"\nWrote {len(results)} rows to {out_path}")
    else:
        print("No results to write")

    # Print summary
    by_key = defaultdict(list)
    for r in results:
        key = (r["agent"], r["skill_mode"])
        by_key[key].append(r["outcome"])

    print("\n=== Summary ===")
    for (agent, skill), outcomes in sorted(by_key.items()):
        counts = {}
        for o in outcomes:
            counts[o] = counts.get(o, 0) + 1
        f2p = counts.get("f2p", 0)
        total = len(outcomes)
        print(f"  {agent} {skill}: {f2p}/{total} f2p  {dict(counts)}")


if __name__ == "__main__":
    main()
