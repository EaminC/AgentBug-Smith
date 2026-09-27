#!/usr/bin/env python3
"""
Batch Patch Generator using AutoCodeRover.
Iterates over SWE issue artifacts, checks out base_sha, executes ACR local-issue,
and writes generated patches to output_dir/result_<issue_id>/generated_patch.diff.

How to run:
python run_acr_batch.py \
  --artifacts-dir ./artifacts \
  --output-dir ./acr_patches \
  --acr-root /root/auto-code-rover \
  --model gpt-4o-mini-2024-07-18
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env or os.environ.copy(),
        check=False,
        text=True,
        capture_output=True,
    )


def solve_single_issue_acr(
    artifact_dir: Path,
    output_dir: Path,
    repos_cache_dir: Path,
    model_name: str,
    acr_root_dir: Path,
):
    issue_folder = artifact_dir.name
    print("\n" + "=" * 60)
    print(f"[*] Processing Artifact: {issue_folder}")
    print("=" * 60)

    # 1. Parse Issue Artifact JSON
    json_files = sorted(list(artifact_dir.glob("issue_*.json"))) or sorted(list(artifact_dir.glob("*.json")))
    if not json_files:
        print(f"[-] No issue JSON found in {artifact_dir}. Skipping.")
        return

    with open(json_files[0], "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    issue_num = str(issue_data.get("number") or issue_folder)
    linked_prs = issue_data.get("linked_prs", [])
    base_sha = linked_prs[0].get("base_sha") if linked_prs else issue_data.get("base_sha")
    raw_url = issue_data.get("url", "")
    repo_url = (raw_url.split("/issues/")[0] + ".git") if "/issues/" in raw_url else raw_url

    title = issue_data.get("title", "")
    body = issue_data.get("body", "")
    problem_statement = f"Issue Title: {title}\n\nDescription:\n{body}"

    # Setup directories
    patch_target_dir = output_dir / f"result_{issue_folder}"
    patch_target_dir.mkdir(parents=True, exist_ok=True)
    patch_file_path = patch_target_dir / "generated_patch.diff"
    log_file_path = patch_target_dir / "acr_run.log"

    workspace_path = repos_cache_dir / f"acr_ws_{issue_num}"
    if workspace_path.exists():
        shutil.rmtree(workspace_path)

    # Write problem statement text file for ACR
    prompt_file = patch_target_dir / "problem_statement.txt"
    prompt_file.write_text(problem_statement, encoding="utf-8")

    try:
        # 2. Clone and checkout base buggy commit
        print(f"[*] Cloning {repo_url} at commit {base_sha}...")
        clone_res = run_cmd(["git", "clone", repo_url, str(workspace_path)])
        if clone_res.returncode != 0:
            print(f"[-] Git clone failed: {clone_res.stderr}")
            return

        if base_sha:
            run_cmd(["git", "checkout", base_sha], cwd=workspace_path)

        # 3. Construct ACR CLI invocation using local-issue
        acr_entry = acr_root_dir / "ACR.py"
        acr_output_dir = patch_target_dir / "acr_output"
        acr_output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(acr_entry),
            "local-issue",
            "--model", model_name,
            "--local-repo", str(workspace_path.resolve()),
            "--issue-file", str(prompt_file.resolve()),
            "--output-dir", str(acr_output_dir.resolve()),
            "--task-id", issue_folder,
        ]

        print(f"[*] Launching AutoCodeRover (local-issue)...")
        acr_env = os.environ.copy()
        acr_env["PYTHONPATH"] = f"{str(acr_root_dir)}:{acr_env.get('PYTHONPATH', '')}"

        run_res = run_cmd(cmd, cwd=acr_root_dir, env=acr_env)

        # Save run log
        log_content = f"STDOUT:\n{run_res.stdout}\n\nSTDERR:\n{run_res.stderr}"
        log_file_path.write_text(log_content, encoding="utf-8")

        # 4. Extract Git Diff or ACR generated patch file
        diff_res = run_cmd(["git", "diff"], cwd=workspace_path)
        patch_text = diff_res.stdout.strip()

        # Check ACR output directory if git diff was empty
        if not patch_text:
            found_patches = list(acr_output_dir.rglob("*.patch")) + list(acr_output_dir.rglob("*.diff"))
            if found_patches:
                patch_text = found_patches[0].read_text(encoding="utf-8").strip()

        if patch_text:
            patch_file_path.write_text(patch_text + "\n", encoding="utf-8")
            print(f"[✓] Generated patch saved: {patch_file_path}")
        else:
            print("[-] ACR finished with empty diff (no patch generated).")

    except Exception as e:
        print(f"[-] Execution error on {issue_folder}: {e}")
        log_file_path.write_text(f"Error: {str(e)}", encoding="utf-8")
    finally:
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)
        if prompt_file.exists():
            prompt_file.unlink()


def main():
    parser = argparse.ArgumentParser(description="Batch generate SWE patches using AutoCodeRover.")
    parser.add_argument("--artifacts-dir", type=Path, required=True, help="Directory with issue artifact folders.")
    parser.add_argument("--output-dir", type=Path, default=Path("./acr_patches"), help="Output directory for diffs.")
    parser.add_argument("--repos-cache", type=Path, default=Path("./.acr_cache"), help="Temporary workspace cache.")
    parser.add_argument("--acr-root", type=Path, default=Path("/root/auto-code-rover"), help="Path to auto-code-rover repo.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini-2024-07-18", help="ACR model name.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.repos_cache.mkdir(parents=True, exist_ok=True)

    artifacts = sorted([p for p in args.artifacts_dir.iterdir() if p.is_dir() and not p.name.startswith(".")])
    print(f"Found {len(artifacts)} issues to process.")

    for art in artifacts:
        solve_single_issue_acr(
            artifact_dir=art,
            output_dir=args.output_dir,
            repos_cache_dir=args.repos_cache,
            model_name=args.model,
            acr_root_dir=args.acr_root,
        )

    if args.repos_cache.exists():
        shutil.rmtree(args.repos_cache, ignore_errors=True)


if __name__ == "__main__":
    main()