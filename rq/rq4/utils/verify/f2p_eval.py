#!/usr/bin/env python3
"""f2p_eval.py — standalone f2p evaluation for RQ4 rollout artifacts.

Usage:
    python f2p_eval.py \
        --patch data/verify/runs/.../patch.txt \
        --issue-json data/verify/_pool/.../issue.json \
        --base-sha c0298319ee00ab7c88ce7087b702a544395e1e3a \
        --repo-dir /home/anonymous/AgentBug-Smith/data/strands-agents_harness-sdk \
        --test-relpath tests/agentsmith_fail2pass_1208.py
"""
import argparse, asyncio, json, subprocess, shutil, sys, time
from pathlib import Path

REPO_ROOT = Path("/home/anonymous/Desktop/RQ4")


def _run_docker_build(repo_dir: Path, dockerfile: Path, tag: str) -> bool:
    r = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64",
         "-f", str(dockerfile), "-t", tag, str(repo_dir)],
        capture_output=True, text=True, timeout=600,
    )
    return r.returncode == 0


def _run_test_in_container(tag: str, test_relpath: str) -> tuple[int, str]:
    """Run pytest in container. Returns (exit_code, tail_of_output)."""
    cmd = ["docker", "run", "--rm", "--network=none",
           "-v", f"{REPO_ROOT / 'agent' / 'config' / '.env'}:/env.env:ro",
           tag,
           "bash", "-c",
           f"pip install --quiet opentelemetry-sdk mcp opentelemetry-instrumentation-threading watchdog 2>/dev/null; "
           f"python -m pytest {test_relpath} -v --tb=short 2>&1"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return r.returncode, (r.stdout + r.stderr)[-3000:]


async def _run_f2p_verify(
    repo_dir: Path,
    base_sha: str,
    patch_text: str,
    issue_json_path: Path,
    test_relpath: str,
    dockerfile_name: str = "env.dockerfile",
) -> tuple[str, str]:
    """Verify fail2pass outcome. Returns (outcome, report)."""
    tmp_repo = Path(f"/tmp/f2p_eval_{int(time.time())}")
    if tmp_repo.exists():
        shutil.rmtree(tmp_repo)
    shutil.copytree(repo_dir, tmp_repo)

    # Reset to base SHA
    subprocess.run(["git", "-C", str(tmp_repo), "checkout", base_sha],
                   capture_output=True, check=False)
    subprocess.run(["git", "-C", str(tmp_repo), "reset", "--hard", base_sha],
                   capture_output=True, check=False)

    # Copy test + dockerfile
    pool_dir = issue_json_path.parent
    df = pool_dir / dockerfile_name
    test_file = pool_dir / test_relpath.lstrip("tests/")
    test_file_name = test_relpath.split("/")[-1]

    shutil.copy2(df, tmp_repo / dockerfile_name)
    (tmp_repo / "tests").mkdir(exist_ok=True)
    if test_file.exists():
        shutil.copy2(test_file, tmp_repo / test_relpath)

    # Build base image
    base_tag = f"f2p_base_{int(time.time())}"
    ok = _run_docker_build(tmp_repo, tmp_repo / dockerfile_name, base_tag)
    if not ok:
        shutil.rmtree(tmp_repo)
        return "error", "docker build failed"

    # Run test before patch
    rc1, out1 = _run_test_in_container(base_tag, test_relpath)

    # Apply patch
    r = subprocess.run(["git", "-C", str(tmp_repo), "apply"],
                       input=patch_text.encode(), capture_output=True)
    if r.returncode != 0:
        shutil.rmtree(tmp_repo)
        return "error", f"git apply failed: {r.stderr.decode()[-500]}"

    # Build patched image  <-- rebuild AFTER patch so Dockerfile pip install picks up the new code
    patched_tag = f"f2p_patched_{int(time.time())}"
    ok = _run_docker_build(tmp_repo, tmp_repo / dockerfile_name, patched_tag)
    if not ok:
        shutil.rmtree(tmp_repo)
        return "error", "docker build failed (after patch)"

    # Run test after patch
    rc2, out2 = _run_test_in_container(patched_tag, test_relpath)

    shutil.rmtree(tmp_repo)

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
    p = argparse.ArgumentParser()
    p.add_argument("--patch", required=True, type=Path)
    p.add_argument("--issue-json", required=True, type=Path)
    p.add_argument("--base-sha", required=True)
    p.add_argument("--repo-dir", required=True, type=Path)
    p.add_argument("--test-relpath", default="tests/agentsmith_fail2pass_TEST.py")
    args = p.parse_args()

    patch_text = args.patch.read_text()
    outcome, report = asyncio.run(_run_f2p_verify(
        repo_dir=args.repo_dir,
        base_sha=args.base_sha,
        patch_text=patch_text,
        issue_json_path=args.issue_json,
        test_relpath=args.test_relpath,
    ))
    print(f"Outcome: {outcome}")
    print(report)


if __name__ == "__main__":
    main()
