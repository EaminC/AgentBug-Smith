#!/usr/bin/env python3
"""
Evaluate Fail-to-Pass (F2P) reproducibility on SWE issue artifacts.

Workflow per issue artifact:
1. Parse issue_*.json, env.dockerfile, and the reproduction test script.
2. Clone target repository and checkout base_sha (buggy commit).
3. Inject the reproduction test script into the workspace.
4. Build the isolated Docker environment using the repository context.
5. Run test inside container -> Must FAIL.
6. Apply patch (from issue_*.json or generated diff).
7. Run test inside container -> Must PASS.
8. Clean up repository workspace and transient Docker image.

How to run: 
1. Test Ground-truth patches (from issue_*.json):
python evaluate_f2p.py \
  --artifacts-dir ./artifacts \
  --output-dir ./f2p_ground_truth_eval \
  --patch-mode issue_json

2. Test Agent-Generated Patches
python evaluate_f2p.py \
  --artifacts-dir ./artifacts \
  --output-dir ./f2p_agent_eval \
  --patch-mode generated_diff \
  --custom-patches-dir ./patches

Eval results structure:
f2p_eval_results/
├── f2p_eval_summary.json
├── eval_issue_141_20260729T075605Z/
│   ├── env.dockerfile
│   ├── step1_fail_execution.log   # Verifies it failed on buggy commit
│   └── step2_pass_execution.log   # Verifies it passed after applying the patch
└── eval_issue_88_20260809T003219Z/
    ├── env.dockerfile
    ├── step1_fail_execution.log
    └── step2_pass_execution.log
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import tomllib
from pathlib import Path
from datetime import datetime, timezone


def get_normalized_package_name(workspace_repo: Path) -> str | None:
    """
    Extracts package name from pyproject.toml or setup.py and normalizes it
    according to PEP 503 / setuptools-scm conventions (uppercase, hyphens to underscores).
    """
    pyproject_path = workspace_repo / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
            raw_name = data.get("project", {}).get("name") or data.get("tool", {}).get("poetry", {}).get("name")
            if raw_name:
                return re.sub(r"[-_.]+", "_", raw_name).upper()
        except Exception:
            pass

    setup_py_path = workspace_repo / "setup.py"
    if setup_py_path.exists():
        try:
            content = setup_py_path.read_text(encoding="utf-8")
            match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return re.sub(r"[-_.]+", "_", match.group(1)).upper()
        except Exception:
            pass

    return None


def run_cmd(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Runs a subprocess command with clean logging."""
    print(f"[EXEC] {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def inject_real_env_keys(
    dockerfile_path: Path, 
    output_dockerfile_path: Path, 
    workspace_repo: Path | None = None
) -> None:
    """Replaces placeholder API keys in env.dockerfile with host environment variables."""
    content = dockerfile_path.read_text(encoding="utf-8")

    key_mappings = {
        "FORGE_API_KEY": os.getenv("FORGE_API_KEY", "forge_key"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "openai_key"),
        "OPENAI_KEY": os.getenv("OPENAI_KEY", "openai_key"),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "openai_base_url"),
        "TAVILY_API_KEY": os.getenv("TAVILY_API_KEY", "tvlv_key"),
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", "github_key"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "anthropic_key"),
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "anthropic_base_url"),
        "MODEL": os.getenv("MODEL", "gpt-4.1-mini"),
    }

    injected_flags = [
        "\n# --- Universal Build & Dynamic Versioning Overrides ---",
        'ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"',
        'ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"',
        'ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"',
        "RUN git config --global --add safe.directory '*' || true",
    ]

    # Dynamically resolve target repository name if available
    if workspace_repo and workspace_repo.exists():
        pkg_name = get_normalized_package_name(workspace_repo)
        if pkg_name:
            injected_flags.append(f'ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_{pkg_name}="0.0.1.dev0"')

    injected_flags.append("# -----------------------------------------------------\n")
    
    lines = []
    from_found = False

    for line in content.splitlines():
        # Replace dummy env values
        replaced = False
        for env_var, real_val in key_mappings.items():
            if line.strip().startswith(f"ENV {env_var}=") or line.strip().startswith(f'ENV "{env_var}"='):
                lines.append(f'ENV {env_var}="{real_val}"')
                replaced = True
                break
        
        if not replaced:
            lines.append(line)

        # Inject right after the first FROM instruction
        if not from_found and line.strip().upper().startswith("FROM "):
            lines.extend(injected_flags)
            from_found = True

    # Fallback if no FROM was detected for any reason
    if not from_found:
        lines = injected_flags + lines

    output_dockerfile_path.write_text("\n".join(lines), encoding="utf-8")


def run_test_in_container(
    image_tag: str,
    workspace_repo: Path,
    relative_test_path: str,
    timeout_seconds: int = 300
) -> tuple[int, str]:
    """Runs pytest inside the Docker container and returns (exit_code, output_log)."""
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{workspace_repo.resolve()}:/app",
        "-w", "/app",
        image_tag,
        "pytest", "-v", relative_test_path
    ]

    try:
        proc = subprocess.run(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_seconds,
        )
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired:
        return -1, "Test execution timed out inside the container."
    except Exception as e:
        return -2, f"Failed to execute test container: {str(e)}"


def apply_patch_to_workspace(
    workspace_repo: Path,
    patch_mode: str,
    issue_data: dict,
    custom_patches_dir: Path | None,
    issue_folder_name: str
) -> tuple[bool, str]:
    """
    Applies either:
    1. The ground-truth patch extracted from issue_*.json (linked_prs[0].patch)
    2. A custom/generated patch from an external folder (e.g. mini-swe-agent output)
    """
    patch_content = ""

    if patch_mode == "issue_json":
        linked_prs = issue_data.get("linked_prs", [])
        if not linked_prs or not linked_prs[0].get("patch"):
            return False, "No patch found inside linked_prs in issue JSON."
        patch_content = linked_prs[0]["patch"]

    elif patch_mode == "generated_diff":
        if not custom_patches_dir:
            return False, "--custom-patches-dir must be specified when using 'generated_diff' mode."
        
        # Look for patch files named generated_patch.diff, patch.diff, or *.diff
        candidate_dirs = [
            custom_patches_dir / f"result_{issue_folder_name}",
            custom_patches_dir / issue_folder_name,
            custom_patches_dir
        ]
        
        patch_file = None
        for cd in candidate_dirs:
            if cd.exists():
                for name in ["generated_patch.diff", "patch.diff", f"{issue_folder_name}.diff"]:
                    if (cd / name).exists():
                        patch_file = cd / name
                        break
            if patch_file:
                break

        if not patch_file:
            return False, f"Could not find patch diff in {custom_patches_dir} for {issue_folder_name}."
        
        patch_content = patch_file.read_text(encoding="utf-8")

    if not patch_content.strip():
        return False, "Patch content is empty."

    # Write patch to a temporary file in workspace and apply via git apply
    temp_patch_path = workspace_repo / "temp_eval_patch.diff"
    temp_patch_path.write_text(patch_content, encoding="utf-8")

    apply_proc = run_cmd(["git", "apply", "--whitespace=nowarn", str(temp_patch_path.name)], cwd=workspace_repo, check=False)
    
    # Cleanup temp diff file
    temp_patch_path.unlink(missing_ok=True)

    if apply_proc.returncode != 0:
        # Fallback to 3-way merge apply if standard apply fails
        fallback_proc = run_cmd(["git", "apply", "-3", "--whitespace=nowarn", str(temp_patch_path.name)], cwd=workspace_repo, check=False)
        if fallback_proc.returncode != 0:
            return False, f"Git apply failed:\n{apply_proc.stderr or apply_proc.stdout}"

    return True, "Patch successfully applied."


def evaluate_single_artifact(
    artifact_dir: Path,
    output_base_dir: Path,
    repos_cache_dir: Path,
    patch_mode: str,
    custom_patches_dir: Path | None
) -> dict:
    """Evaluates one issue folder for fail-to-pass status."""
    issue_folder_name = artifact_dir.name
    print("\n" + "=" * 60)
    print(f"[*] Testing Artifact: {issue_folder_name}")
    print("=" * 60)

    # 1. Discover files
    dockerfile_path = artifact_dir / "env.dockerfile"
    if not dockerfile_path.exists():
        dockerfile_path = artifact_dir / "Dockerfile"

    issue_json_candidates = sorted(list(artifact_dir.glob("issue_*.json")))
    if not issue_json_candidates:
        issue_json_candidates = sorted(list(artifact_dir.glob("*.json")))

    test_files = list(artifact_dir.glob("agentsmith_fail2pass_*.*")) or list(artifact_dir.glob("test_*.py"))

    if not dockerfile_path.exists() or not issue_json_candidates or not test_files:
        print(f"[-] Missing required artifacts in {artifact_dir}. Skipping.")
        return {"issue": issue_folder_name, "status": "skipped", "reason": "missing_artifacts"}

    issue_json_path = issue_json_candidates[0]
    test_script_path = test_files[0]

    with open(issue_json_path, "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    issue_num = str(issue_data.get("number") or issue_folder_name)
    linked_prs = issue_data.get("linked_prs", [])
    base_sha = linked_prs[0].get("base_sha") if linked_prs else issue_data.get("base_sha")

    raw_url = issue_data.get("url", "")
    repo_url = (raw_url.split("/issues/")[0] + ".git") if "/issues/" in raw_url else raw_url

    # Setup directories and logs
    eval_output_dir = output_base_dir / f"eval_{issue_folder_name}"
    eval_output_dir.mkdir(parents=True, exist_ok=True)
    fail_log_path = eval_output_dir / "step1_fail_execution.log"
    pass_log_path = eval_output_dir / "step2_pass_execution.log"

    workspace_repo = repos_cache_dir / f"eval_repo_{issue_num}"
    image_tag = f"f2p-eval-env-{issue_num.lower()}:latest"

    try:
        # STEP 1: CLONE & CHECKOUT BUGGY COMMIT
        print(f"[1/5] Cloning repo and checking out base commit ({base_sha})...")
        if workspace_repo.exists():
            shutil.rmtree(workspace_repo)

        try:
            run_cmd(["git", "clone", repo_url, str(workspace_repo)])
            if base_sha:
                run_cmd(["git", "checkout", base_sha], cwd=workspace_repo)
        except subprocess.CalledProcessError as e:
            return {"issue": issue_folder_name, "verdict": "ERROR", "reason": "git_clone_failed", "details": e.stderr}

        # Inject reproduction test script
        dest_test_path = workspace_repo / "tests" / test_script_path.name
        dest_test_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(test_script_path, dest_test_path)
        init_file = dest_test_path.parent / "__init__.py"
        if not init_file.exists():
            init_file.touch()

        relative_test_path = f"tests/{test_script_path.name}"

        # STEP 2: BUILD DOCKER ENVIRONMENT
        print(f"[2/5] Building Docker environment '{image_tag}'...")
        sanitized_dockerfile = eval_output_dir / "env.dockerfile"
        inject_real_env_keys(
            dockerfile_path=dockerfile_path,
            output_dockerfile_path=sanitized_dockerfile,
            workspace_repo=workspace_repo
        )

        try:
            run_cmd([
                "docker", "build",
                "-t", image_tag,
                "-f", str(sanitized_dockerfile.resolve()),
                str(workspace_repo.resolve())
            ])
        except subprocess.CalledProcessError as e:
            return {"issue": issue_folder_name, "verdict": "ERROR", "reason": "docker_build_failed", "details": e.stderr}

        # STEP 3: RUN TEST ON BUGGY REPO (MUST FAIL)
        print(f"[3/5] Verifying FAIL state on buggy commit...")
        fail_code, fail_output = run_test_in_container(image_tag, workspace_repo, relative_test_path)
        fail_log_path.write_text(fail_output, encoding="utf-8")

        if fail_code == 0:
            print("[-] FAIL Verification Failed: Test passed on the buggy commit (Expected Failure).")
            return {
                "issue": issue_folder_name,
                "verdict": "FAIL_VERIFICATION_FAILED",
                "reason": "Test unexpectedly passed on base commit (No bug detected)."
            }
        print("[+] Test successfully FAILED on base commit as expected.")

        # STEP 4: APPLY PATCH
        print(f"[4/5] Applying patch using mode '{patch_mode}'...")
        applied_ok, apply_msg = apply_patch_to_workspace(
            workspace_repo=workspace_repo,
            patch_mode=patch_mode,
            issue_data=issue_data,
            custom_patches_dir=custom_patches_dir,
            issue_folder_name=issue_folder_name
        )
        if not applied_ok:
            print(f"[-] Patch application failed: {apply_msg}")
            return {"issue": issue_folder_name, "verdict": "PATCH_APPLY_FAILED", "reason": apply_msg}

        # STEP 5: RUN TEST ON PATCHED REPO (MUST PASS)
        print(f"[5/5] Verifying PASS state on patched codebase...")
        pass_code, pass_output = run_test_in_container(image_tag, workspace_repo, relative_test_path)
        pass_log_path.write_text(pass_output, encoding="utf-8")

        if pass_code != 0:
            print("[-] PASS Verification Failed: Test failed after patch was applied.")
            return {
                "issue": issue_folder_name,
                "verdict": "PASS_VERIFICATION_FAILED",
                "reason": "Test still failing after patch applied."
            }

        print("[✓] SUCCESS: Verified Fail-to-Pass (F2P) reproducibility.")
        return {
            "issue": issue_folder_name,
            "verdict": "F2P_SUCCESS",
            "base_sha": base_sha,
            "test_file": relative_test_path
        }

    finally:
        # CLEANUP
        print(f"[*] Cleaning up workspace and image for {issue_folder_name}...")
        if workspace_repo.exists():
            shutil.rmtree(workspace_repo, ignore_errors=True)
        try:
            run_cmd(["docker", "rmi", image_tag], check=False)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Evaluate Fail-to-Pass (F2P) behavior across saved SWE issue artifacts.")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        required=True,
        help="Path to artifacts directory containing issue folders (e.g., ./artifacts/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./f2p_eval_results"),
        help="Directory to save evaluation logs and summary report.",
    )
    parser.add_argument(
        "--repos-cache",
        type=Path,
        default=Path("./.f2p_repos_cache"),
        help="Temporary directory for repo cloning.",
    )
    parser.add_argument(
        "--patch-mode",
        choices=["issue_json", "generated_diff"],
        default="issue_json",
        help="Where to obtain the patch from: 'issue_json' (default ground-truth) or 'generated_diff' (agent generated).",
    )
    parser.add_argument(
        "--custom-patches-dir",
        type=Path,
        default=None,
        help="Path to folder containing agent-generated patch files (used when --patch-mode is 'generated_diff').",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.repos_cache.mkdir(parents=True, exist_ok=True)

    artifact_folders = [
        p for p in args.artifacts_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]

    print(f"Found {len(artifact_folders)} artifacts to evaluate.")
    print(f"Active patch mode: {args.patch_mode}")

    results = []
    try:
        for folder in sorted(artifact_folders):
            res = evaluate_single_artifact(
                artifact_dir=folder,
                output_base_dir=args.output_dir,
                repos_cache_dir=args.repos_cache,
                patch_mode=args.patch_mode,
                custom_patches_dir=args.custom_patches_dir
            )
            results.append(res)
    finally:
        if args.repos_cache.exists():
            shutil.rmtree(args.repos_cache, ignore_errors=True)

    # Compile Summary
    success_count = sum(1 for r in results if r.get("verdict") == "F2P_SUCCESS")
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": len(artifact_folders),
        "f2p_success_count": success_count,
        "f2p_success_rate": f"{(success_count / len(artifact_folders) * 100):.2f}%" if artifact_folders else "0%",
        "results": results
    }

    summary_file = args.output_dir / "f2p_eval_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"[✓] F2P Evaluation Complete!")
    print(f"[✓] Success Rate: {summary['f2p_success_rate']} ({success_count}/{len(artifact_folders)})")
    print(f"[✓] Detailed summary written to: {summary_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()