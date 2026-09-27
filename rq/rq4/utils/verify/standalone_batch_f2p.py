#!/usr/bin/env python3
"""standalone_batch_f2p.py — self-contained f2p evaluation.

Does NOT depend on AgentSmith's testrun/verify.
Builds two Docker images per patch (before/after), runs pytest in each.
"""
import argparse, csv, json, shutil, subprocess, sys, time
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path("/home/anonymous/Desktop/RQ4")
AGENTSMITH_ROOT = Path("/home/anonymous/AgentBug-Smith")

COMBOS = [
    "mini-swe-agent_40", "mini-swe-agent_60", "mini-swe-agent_80",
    "openhands_40", "openhands_60", "openhands_80",
]
PILOT30_IDS = ["issue-1208", "issue-1351", "issue-1689", "issue-3493", "issue-1528"]


def agent_repo_dir(repo: str) -> Path:
    owner, name = repo.split("/", 1)
    return AGENTSMITH_ROOT / "data" / f"{owner}_{name}"


def get_index(combo: str) -> dict:
    """Return dict {issue_id: {base_sha, repo, test_relpath}}."""
    idx = REPO_ROOT / f"data/verify/issue_index_pilot30_{combo}.jsonl"
    result = {}
    for line in idx.read_text().splitlines():
        d = json.loads(line)
        result[d["id"]] = d
    return result


def _docker_build(tag: str, dockerfile: Path, context: Path) -> bool:
    """Build docker image. Returns True on success."""
    r = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64",
         "-f", str(dockerfile), "-t", tag, str(context)],
        capture_output=True, text=True, timeout=3600,
    )
    return r.returncode == 0


def _docker_run_pytest(tag: str, workdir: str, test_relpath: str) -> tuple[int, str]:
    """Run pytest in container. Returns (exit_code, output_tail)."""
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{REPO_ROOT / 'agent/config/.env'}:/env.env:ro",
        "-w", workdir,
        tag,
        "bash", "-c",
        f"set -a && . /env.env && set +a && "
        f"pip install --quiet opentelemetry-sdk mcp opentelemetry-instrumentation-threading watchdog 2>/dev/null; "
        f"python -m pytest {test_relpath} -v --tb=short 2>&1",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    return r.returncode, (r.stdout + r.stderr)[-3000:]


def eval_patch(
    repo_dir: Path,
    pool_dir: Path,
    base_sha: str,
    patch_text: str,
    test_relpath: str,
) -> tuple[str, str]:
    """Run full f2p eval. Returns (outcome, report)."""
    ts = int(time.time() * 1000)
    tmp = Path(f"/tmp/f2p_{ts}")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(repo_dir, tmp)

    # Reset to base SHA
    subprocess.run(["git", "-C", str(tmp), "checkout", base_sha],
                   capture_output=True, check=False)
    subprocess.run(["git", "-C", str(tmp), "reset", "--hard", base_sha],
                   capture_output=True, check=False)

    # Copy env.dockerfile and test
    df = pool_dir / "env.dockerfile"
    shutil.copy2(df, tmp / "env.dockerfile")
    if test_relpath:
        test_name = test_relpath.split("/")[-1]
        test_src = pool_dir / test_name
        if test_src.exists():
            test_dir = tmp / "/".join(test_relpath.split("/")[:-1])
            test_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(test_src, tmp / test_relpath)

    workdir = "/app"
    tag_base = f"f2p_base_{ts}"
    tag_patched = f"f2p_patch_{ts}"

    # Build base image (from base SHA state)
    ok = _docker_build(tag_base, tmp / "env.dockerfile", tmp)
    if not ok:
        shutil.rmtree(tmp)
        return "error", "docker build failed (base)"

    # Run test before patch
    rc1, out1 = _docker_run_pytest(tag_base, workdir, test_relpath)

    # Apply patch to tmp repo (MUST be before second build)
    r = subprocess.run(
        ["git", "-C", str(tmp), "apply", "--stat"],
        input=patch_text.encode(), capture_output=True,
    )
    if r.returncode != 0:
        shutil.rmtree(tmp)
        return "error", f"git apply failed (stat):\n{(r.stderr or b'').decode(errors='replace')[-500:]}"

    r2 = subprocess.run(
        ["git", "-C", str(tmp), "apply"],
        input=patch_text.encode(), capture_output=True,
    )
    if r2.returncode != 0:
        shutil.rmtree(tmp)
        return "error", f"git apply failed:\n{(r2.stderr or b'').decode(errors='replace')[-500:]}"

    # Build patched image (from patched state)
    ok = _docker_build(tag_patched, tmp / "env.dockerfile", tmp)
    if not ok:
        shutil.rmtree(tmp)
        return "error", "docker build failed (patched)"

    # Run test after patch
    rc2, out2 = _docker_run_pytest(tag_patched, workdir, test_relpath)

    shutil.rmtree(tmp)

    # Determine outcome
    if rc1 != 0 and rc2 == 0:
        outcome = "f2p"
    elif rc1 != 0 and rc2 != 0:
        outcome = "f2f"
    elif rc1 == 0 and rc2 == 0:
        outcome = "p2p"
    elif rc1 == 0 and rc2 != 0:
        outcome = "p2f"
    else:
        outcome = "error"

    report = (f"rc_before={rc1}  rc_after={rc2}\n"
              f"=== before ===\n{out1[-1000:]}\n"
              f"=== after ===\n{out2[-1000:]}")
    return outcome, report


def main():
    results = []
    for combo in COMBOS:
        idx = get_index(combo)
        agent = combo.split("_")[0]
        scale = combo.split("_")[1]
        run_base = REPO_ROOT / f"data/verify/runs/{combo}"

        for issue_id in PILOT30_IDS:
            if issue_id not in idx:
                continue
            meta = idx[issue_id]
            base_sha = meta.get("base_sha", "")
            repo_name = meta.get("repo", "")
            test_relpath = meta.get("test_relpath", "")

            repo_dir = agent_repo_dir(repo_name)
            pool_dir = REPO_ROOT / f"data/verify/_pool/{repo_name.replace('/', '__')}__{issue_id}"

            if not repo_dir.exists():
                print(f"  SKIP {issue_id}: repo not found")
                continue

            for skill in ["with_skill", "without_skill"]:
                patch_dir = run_base / f"{repo_name.replace('/', '__')}__{issue_id}" / skill
                patch_path = patch_dir / "patch.txt"

                if not patch_path.exists():
                    results.append({
                        "agent": agent, "scale": scale,
                        "skill": skill, "issue": issue_id,
                        "has_patch": False, "outcome": "", "report": "no patch"
                    })
                    continue

                print(f"  {combo} {issue_id} {skill}...", flush=True)
                patch_text = patch_path.read_text()
                outcome, report = eval_patch(
                    repo_dir, pool_dir, base_sha,
                    patch_text, test_relpath,
                )
                results.append({
                    "agent": agent, "scale": scale,
                    "skill": skill, "issue": issue_id,
                    "has_patch": True, "outcome": outcome,
                    "report": report[:500],
                })
                print(f"    → {outcome}")

    # Write CSV
    out_path = REPO_ROOT / "results/rq4/pilot30_scores.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["agent", "scale", "skill", "issue", "has_patch", "outcome", "report"]
    with open(out_path, "w") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)

    print(f"\nWrote {len(results)} rows to {out_path}")

    # Summary
    print("\n=== Summary ===")
    by = defaultdict(list)
    for r in results:
        by[(r["agent"], r["skill"])].append(r["outcome"])

    for (agent, skill), outcomes in sorted(by.items()):
        c = defaultdict(int)
        for o in outcomes:
            c[o] += 1
        n = len(outcomes)
        f2p = c.get("f2p", 0)
        print(f"  {agent} {skill}: {f2p}/{n} f2p  | {dict(c)}")


if __name__ == "__main__":
    main()
