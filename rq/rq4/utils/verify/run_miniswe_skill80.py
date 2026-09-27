#!/usr/bin/env python3
"""run_miniswe_skill80.py — ALFIN-style per-issue mini-swe-agent batch.

Adapter of https://github.com/alfin06/mini-swe-agent/blob/main/exp/
run_mini_swe_agent_batch.py to this project's pool layout.

Differences from upstream:
  * No re-cloning upstream-style `git clone ${url}.git`; we use the
    pool's repo clone at `${AGENTSMITH_ROOT}/<owner>_<name>` and just
    `git checkout <base_sha>` (already what alfin06 effectively does,
    but our pool pre-clones).
  * Skill injection: prepend our trained SKILL.md as a `<skill>` block
    inside the `-t` problem statement. *with_skill only.*
  * Idempotent: skips `(issue_id)` whose `<out>/<id>/patch.txt` exists.
  * Always `docker rmi <tag>` after the per-issue run + after scoring.

Run:
  python3 utils/verify/run_miniswe_skill80.py \
      --index data/verify/issue_index_mini-swe-agent_80.jsonl \
      --pool data/verify/_pool \
      --skill-dir agent/skills/mini-swe-agent/80 \
      --out  data/verify/runs/mini-swe-agent_80_withskill \
      --limit 79 --only-test
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "utils"))

DEFAULT_MODEL = os.getenv("MINI_SWE_MODEL", "openai/tuzi-gpt-4.1-mini/gpt-4.1-mini")
TIMEOUT_MIN = int(os.getenv("MINI_SWE_TIMEOUT_MIN", "20"))
TAG_PREFIX = "rq4-ms-skill80"


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd: list[str], *, timeout: int | None = None, check: bool = True, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=check, cwd=cwd)


def sh_safe(cmd: list[str], *, timeout: int | None = None, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Same as sh() but never raises — returns rc=-1 on exception."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, -1, "", str(e))


def agent_repo_path(repo: str) -> Path:
    """Where the pool's repo clone lives on the host. Required so the
    docker build context can `COPY . .` from the right place."""
    root = os.environ.get("AGENTSMITH_ROOT") or "/home/anonymous/AgentBug-Smith"
    slug = repo.replace("/", "_")
    for cand in (Path(root) / "data" / slug, Path(root) / slug):
        if cand.exists() and (cand / ".git").exists():
            return cand
    raise FileNotFoundError(
        f"repo clone not found at {root}/data/{slug} (or {root}/{slug}). "
        f"Clone {repo} into $AGENTSMITH_ROOT/data/ or set AGENTSMITH_ROOT."
    )


def build_skill_prompt(skill_dir: Path, issue: dict) -> str:
    """Compose the problem statement with our skill prepended.

    Layout: <skill>SKILL.md</skill> + <repo_notes?> + ISSUE BODY.
    Tries to load per-repo notes by `owner__name.md`; falls back if absent.
    """
    main = (skill_dir / "SKILL.md").read_text()
    fallback = (skill_dir / "fallback_generic_fix.md").read_text() if (skill_dir / "fallback_generic_fix.md").exists() else ""

    url = issue.get("url", "")
    owner_name = ""
    if "/issues/" in url:
        head = url.split("/issues/", 1)[0]
        parts = head.rstrip("/").split("/")
        if len(parts) >= 2:
            owner_name = f"{parts[-2]}__{parts[-1]}.md"

    repo_notes = ""
    if owner_name:
        rp = skill_dir / "repos" / owner_name
        if rp.exists():
            repo_notes = (
                f"\n\n<repo_notes src=\"repos/{owner_name}\">\n"
                f"{rp.read_text()}\n</repo_notes>\n"
            )
    if not repo_notes:
        repo_notes = (
            f"\n\n<repo_notes src=\"fallback_generic_fix.md\">\n"
            f"{fallback}\n</repo_notes>\n"
        )

    title = issue.get("title", "").strip()
    body = (issue.get("body") or "").strip()
    number = issue.get("number", "")
    issue_block = f"# Issue #{number}: {title}\n\n{body}\n" if number else f"# {title}\n\n{body}\n"

    return (
        "<skill>\n"
        + main
        + "\n</skill>\n"
        + repo_notes
        + "\n--- ISSUE ---\n\n"
        + issue_block
    )


def process_one(
    issue_id: str,
    issue_dir: Path,
    out_dir: Path,
    skill_dir: Path,
    repo_url: str,
    base_sha: str,
    test_relpath: str | None,
) -> dict:
    """Run one issue end-to-end: build docker, run agent, save patch.

    Returns dict with status + paths. Always cleans up the docker image.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    short_id = issue_id.replace("issue-", "")
    image_tag = f"{TAG_PREFIX}-{short_id}:latest"

    patch_path = out_dir / "patch.txt"
    if patch_path.exists() and patch_path.stat().st_size > 0:
        return {"issue": issue_id, "status": "skipped_exists"}

    log(f"[{issue_id}] start  →  image={image_tag}")
    t0 = time.time()

    # 1) Load the verify-pool issue (canonical)
    with (issue_dir / "issue.json").open() as f:
        issue = json.load(f)
    issue_title = issue.get("title", "")
    test_filename = (
        Path(test_relpath).name
        if test_relpath
        else f"agentsmith_fail2pass_{short_id}.py"
    )
    problem_statement = build_skill_prompt(skill_dir, issue)

    # 2) Resolve the repo clone on the host (matches pool dockerfile's COPY . .)
    try:
        repo_dir = agent_repo_path(issue["repo"])
    except FileNotFoundError as e:
        msg = str(e)
        log(f"[{issue_id}] ✗ {msg}")
        return {"issue": issue_id, "status": "no_repo", "error": msg}

    # 3) git checkout base_sha
    sh(["git", "checkout", "-f", base_sha], cwd=repo_dir)
    # Inject fail-to-pass test into tests/ so the agent can reproduce.
    if test_relpath:
        f2p_src = issue_dir / Path(test_relpath).name
        if not f2p_src.exists():
            # try matching by issue number
            cand = list(issue_dir.glob("agentsmith_fail2pass_*.py"))
            f2p_src = cand[0] if cand else None
        if f2p_src and f2p_src.exists():
            dest = repo_dir / test_relpath
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f2p_src, dest)
            init = dest.parent / "__init__.py"
            if not init.exists():
                init.touch()

    # 4) Build docker image using pool's env.dockerfile as base context
    dockerfile_path = issue_dir / "env.dockerfile"
    # Build using the host repo_dir as context (matches pool's COPY . .)
    log(f"[{issue_id}] · docker build …")
    proc = sh_safe(
        ["docker", "build", "-t", image_tag, "-f", str(dockerfile_path), str(repo_dir)],
        timeout=900,
    )
    if proc.returncode != 0:
        log(f"[{issue_id}] ✗ docker build failed (rc={proc.returncode})")
        (out_dir / "build_stderr.txt").write_text(proc.stderr)
        return {"issue": issue_id, "status": "build_failed", "stderr_tail": proc.stderr[-500:]}

    # 5) Run mini-swe-agent inside the image
    log(f"[{issue_id}] · mini-swe-agent …")
    env_args = [
        "-e", "MSWEA_CONFIGURED=true",
        "-e", "MSWEA_COST_TRACKING=ignore_errors",
        "-e", f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}",
        "-e", f"OPENAI_API_BASE={os.getenv('OPENAI_API_BASE', os.getenv('OPENAI_BASE_URL', ''))}",
    ]
    cmd = [
        "docker", "run", "--rm",
        *env_args,
        "-v", f"{repo_dir.resolve()}:/app",
        "-w", "/app",
        image_tag,
        "mini-swe-agent",
        "-c", "mini.yaml",
        "-m", DEFAULT_MODEL,
        "-y",
        "--exit-immediately",
        "-t", problem_statement,
        "-o", f"/app/.mswea_traj.json",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_MIN * 60,
    )
    (out_dir / "agent_stdout.txt").write_text(proc.stdout)
    (out_dir / "agent_stderr.txt").write_text(proc.stderr)
    (out_dir / "agent.json").write_text(json.dumps({
        "issue": issue_id, "exit_code": proc.returncode,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "stdout_tail": proc.stdout[-400:],
    }, indent=2))

    # 6) Extract patch: copy trajectory out + git diff
    sh_safe(["docker", "cp", f"$(docker create --rm {image_tag} true):/app/.mswea_traj.json",
             str(out_dir / "trajectory.json")], timeout=60)

    diff_proc = sh_safe(["git", "diff"], cwd=repo_dir)
    patch_text = diff_proc.stdout
    if patch_text.strip():
        patch_path.write_text(patch_text)
        log(f"[{issue_id}] ✓ patch saved ({len(patch_text)} chars, {time.time()-t0:.1f}s)")
        status = "success"
    else:
        # Even on empty diff, copy intent-to-add diff so we can see attempted edits
        sh_safe(["git", "add", "-A", "--intent-to-add"], cwd=repo_dir)
        diff_proc = sh_safe(["git", "diff"], cwd=repo_dir)
        if diff_proc.stdout.strip():
            patch_path.write_text(diff_proc.stdout)
            log(f"[{issue_id}] ⚠ patch (intent-to-add) saved ({len(diff_proc.stdout)} chars)")
            status = "intent_only"
        else:
            log(f"[{issue_id}] ✗ no patch produced")
            status = "no_patch"

    # 7) Cleanup docker image + restore repo checkout
    sh_safe(["docker", "rmi", "-f", image_tag], timeout=120)
    sh_safe(["git", "checkout", "-f", "HEAD", "--", "."], cwd=repo_dir)
    sh_safe(["git", "clean", "-fd"], cwd=repo_dir)

    return {"issue": issue_id, "status": status, "patch_chars": len(patch_text)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True, type=Path)
    ap.add_argument("--pool", required=True, type=Path,
                    help="Absolute path to data/verify/_pool")
    ap.add_argument("--skill-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path,
                    help="Absolute path to data/verify/runs/<…>_withskill")
    ap.add_argument("--limit", type=int, default=79)
    ap.add_argument("--only-test", action="store_true", default=True)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    summary_path = args.out / "batch_summary.jsonl"

    with args.index.open() as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if args.only_test:
        rows = [r for r in rows if r.get("split") == 1]
    rows = rows[: args.limit]

    log(f"plan: {len(rows)} issues  model={DEFAULT_MODEL}  timeout={TIMEOUT_MIN}m  out={args.out}")

    summary = []
    n_ok = n_empty = n_build = n_repo = 0
    for i, row in enumerate(rows, 1):
        issue_id = row["id"]
        verify_rel = Path(row["verify_dir"])
        verify_dir = args.pool / verify_rel.name
        if not verify_dir.exists():
            log(f"[{i}/{len(rows)}] {issue_id}  ✗ pool dir missing: {verify_rel}")
            n_repo += 1
            summary.append({"issue": issue_id, "status": "no_pool"})
            continue
        out_dir = args.out / verify_rel.name
        try:
            r = process_one(
                issue_id=issue_id,
                issue_dir=verify_dir,
                out_dir=out_dir,
                skill_dir=args.skill_dir,
                repo_url=row["repo"],
                base_sha=row.get("base_sha", ""),
                test_relpath=row.get("test_relpath"),
            )
        except Exception as e:
            log(f"[{i}/{len(rows)}] {issue_id}  ✗ Exception: {e}")
            r = {"issue": issue_id, "status": "exception", "error": str(e)}
        summary.append(r)
        if r["status"] == "success":
            n_ok += 1
        elif r["status"] in ("no_patch",):
            n_empty += 1
        elif r["status"] == "build_failed":
            n_build += 1
        # Save incrementally
        with summary_path.open("w") as f:
            for s in summary:
                f.write(json.dumps(s) + "\n")
        # Disk check every 5
        if i % 5 == 0:
            df = sh_safe(["df", "-h", "/"]).stdout
            for ln in df.splitlines():
                if "/dev" in ln:
                    log(f"  df: {ln}")

    log(f"DONE  ok={n_ok}  empty={n_empty}  build_fail={n_build}  no_repo={n_repo}  →  {summary_path}")


if __name__ == "__main__":
    main()
