#!/usr/bin/env python3
"""
Batch Pipeline: Run mini-swe-agent v2 on multiple issue artifacts to generate patches.
Workflow:
1. Clone repo & checkout base_sha
2. Inject mini-swe-agent into Dockerfile and build environment using repo as context
3. Run mini-swe-agent inside the built Docker container (with MSWEA_COST_TRACKING='ignore_errors')
4. Parse trajectory.json to generate accurate cost.json
5. Extract git diff patch (including untracked files)
6. Clean up workspace and transient Docker images

How to run?
python exp/run_mini_swe_agent_batch.py \
  --artifacts-dir ./artifacts \
  --output-dir ./patches \
  --model "openai/tuzi-deepseek-v3.2/deepseek-v3.2"
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
import re
import tomllib
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_MODEL = os.getenv("MODEL", "openai/tuzi-deepseek-v3.2/deepseek-v3.2")
TIMEOUT_MINUTES = 30

# Rate Cards for target models ($ / token)
MODEL_RATE_CARDS = {
    "gpt-4.1-mini": {
        "uncached_in": 0.40 / 1_000_000,
        "cached_in": 0.10 / 1_000_000,
        "out": 1.60 / 1_000_000,
    },
    "deepseek-v3.2": {
        "uncached_in": 0.28 / 1_000_000,
        "cached_in": 0.028 / 1_000_000,
        "out": 0.42 / 1_000_000,
    },
    "kimi-k2.5": {
        "uncached_in": 0.60 / 1_000_000,
        "cached_in": 0.10 / 1_000_000,
        "out": 2.50 / 1_000_000,
    },
}


def get_model_rates(model_name: str) -> tuple[str, dict]:
    """Matches the model string to one of the 3 supported rate cards."""
    name = model_name.lower()
    if "kimi" in name or "k2.5" in name:
        return "kimi-k2.5", MODEL_RATE_CARDS["kimi-k2.5"]
    elif "deepseek" in name or "v3.2" in name:
        return "deepseek-v3.2", MODEL_RATE_CARDS["deepseek-v3.2"]
    else:
        return "gpt-4.1-mini", MODEL_RATE_CARDS["gpt-4.1-mini"]


def get_normalized_package_name(workspace_repo: Path) -> str | None:
    """Extracts and normalizes package name for setuptools-scm flags."""
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
    """Helper to run shell commands cleanly with logging."""
    print(f"[EXEC] {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=True,
    )


def extract_problem_statement_from_issue_json(issue_data: dict) -> str:
    """Constructs a clean markdown problem statement from issue JSON fields."""
    title = issue_data.get("title", "").strip()
    body = issue_data.get("body", "").strip()
    issue_number = issue_data.get("number", "")

    header = f"# Issue #{issue_number}: {title}" if issue_number else f"# {title}"
    if body:
        return f"{header}\n\n{body}\n"
    return f"{header}\n"


def inject_real_env_keys_and_tools(
    dockerfile_path: Path, 
    output_dockerfile_path: Path, 
    workspace_repo: Path | None = None
) -> None:
    """Replaces dummy API keys and installs mini-swe-agent inside the container image."""
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

    injected_vcs_flags = [
        "\n# --- Universal Build & Dynamic Versioning Overrides ---",
        'ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"',
        'ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"',
        'ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"',
        "RUN git config --global --add safe.directory '*' || true",
    ]

    if workspace_repo and workspace_repo.exists():
        pkg_name = get_normalized_package_name(workspace_repo)
        if pkg_name:
            injected_vcs_flags.append(f'ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_{pkg_name}="0.0.1.dev0"')

    injected_vcs_flags.append("# -----------------------------------------------------\n")

    lines = []
    from_found = False

    for line in content.splitlines():
        replaced = False
        for env_var, real_val in key_mappings.items():
            if real_val and (line.strip().startswith(f"ENV {env_var}=") or line.strip().startswith(f'ENV "{env_var}"=')):
                lines.append(f'ENV {env_var}="{real_val}"')
                replaced = True
                break

        if not replaced:
            lines.append(line)

        # Inject VCS flags immediately after the first FROM instruction
        if not from_found and line.strip().upper().startswith("FROM "):
            lines.extend(injected_vcs_flags)
            from_found = True

    if not from_found:
        lines = injected_vcs_flags + lines

    # Append mini-swe-agent installation and disable setup prompt & cost error halts
    lines.append("\n# Install mini-swe-agent and set configuration flag")
    lines.append("RUN pip install --no-cache-dir mini-swe-agent && \\")
    lines.append("    mkdir -p /root/.config/mini-swe-agent && \\")
    lines.append('    echo "MSWEA_CONFIGURED=true" >> /root/.config/mini-swe-agent/.env && \\')
    lines.append('    echo "MSWEA_COST_TRACKING=ignore_errors" >> /root/.config/mini-swe-agent/.env\n')

    output_dockerfile_path.write_text("\n".join(lines), encoding="utf-8")


def parse_and_calculate_cost(trajectory_path: Path, model_name: str, issue_folder: str) -> dict:
    """Parses trajectory.json from mini-swe-agent and computes token metrics."""
    matched_model, rates = get_model_rates(model_name)
    input_tokens = 0
    cached_tokens = 0
    output_tokens = 0

    if trajectory_path.exists():
        try:
            with open(trajectory_path, "r", encoding="utf-8") as f:
                traj_data = json.load(f)

            # mini-swe-agent trajectory typically saves messages/steps in 'trajectory' or 'history'
            steps = traj_data.get("trajectory") or traj_data.get("history") or []
            for step in steps:
                response = step.get("response", {})
                usage = response.get("usage", {}) or step.get("usage", {})
                if usage:
                    input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
                    output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
                    cached = (
                        usage.get("cache_read_tokens")
                        or usage.get("cache_read_input_tokens")
                        or usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
                        or 0
                    )
                    cached_tokens += int(cached)
        except Exception as e:
            print(f"[-] Warning: Failed to parse trajectory tokens: {e}")

    uncached_in = max(0, input_tokens - cached_tokens)
    cost_usd = (
        (uncached_in * rates["uncached_in"])
        + (cached_tokens * rates["cached_in"])
        + (output_tokens * rates["out"])
    )

    return {
        "instance_id": issue_folder,
        "model": matched_model,
        "raw_model_name": model_name,
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "uncached_tokens": uncached_in,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(cost_usd, 6),
    }


def process_single_issue(
    artifact_dir: Path,
    output_base_dir: Path,
    repos_cache_dir: Path,
    model: str = DEFAULT_MODEL
) -> dict:
    """Processes a single issue artifact folder end-to-end."""
    issue_folder_name = artifact_dir.name
    print("\n" + "=" * 60)
    print(f"[*] Processing: {issue_folder_name}")
    print("=" * 60)

    # 1. Locate Dockerfile and issue_*.json
    dockerfile_path = artifact_dir / "env.dockerfile"
    if not dockerfile_path.exists():
        dockerfile_path = artifact_dir / "Dockerfile"

    issue_json_candidates = sorted(list(artifact_dir.glob("issue_*.json")))
    if not issue_json_candidates:
        issue_json_candidates = sorted(list(artifact_dir.glob("*.json")))

    if not dockerfile_path.exists() or not issue_json_candidates:
        print(f"[-] Missing dockerfile or issue JSON in {artifact_dir}. Skipping.")
        return {"issue": issue_folder_name, "status": "skipped", "reason": "missing_artifacts"}

    issue_json_path = issue_json_candidates[0]
    print(f"[+] Loaded issue configuration from: {issue_json_path.name}")

    with open(issue_json_path, "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    issue_num = str(issue_data.get("number") or issue_folder_name)
    linked_prs = issue_data.get("linked_prs", [])
    base_sha = None
    if linked_prs and isinstance(linked_prs, list):
        base_sha = linked_prs[0].get("base_sha")
    if not base_sha:
        base_sha = issue_data.get("base_sha")

    raw_url = issue_data.get("url", "")
    if "/issues/" in raw_url:
        repo_url = raw_url.split("/issues/")[0] + ".git"
    else:
        repo_url = raw_url

    problem_statement = extract_problem_statement_from_issue_json(issue_data)

    test_files = list(artifact_dir.glob("agentsmith_fail2pass_*.*")) or list(artifact_dir.glob("test_*.py"))
    test_script_path = test_files[0] if test_files else None

    # Setup output paths
    run_output_dir = output_base_dir / f"result_{issue_folder_name}"
    run_output_dir.mkdir(parents=True, exist_ok=True)
    patch_output_path = run_output_dir / "generated_patch.diff"
    log_file_path = run_output_dir / "agent_run.log"
    trajectory_file_path = run_output_dir / "trajectory.json"
    cost_file_path = run_output_dir / "cost.json"
    problem_statement_file = run_output_dir / "problem_statement.txt"
    problem_statement_file.write_text(problem_statement, encoding="utf-8")

    workspace_repo = repos_cache_dir / f"repo_issue_{issue_num}"
    image_tag = f"swe-agent-env-issue-{issue_num.lower()}:latest"

    try:
        # -------------------------------------------------------------
        # CLONE & CHECKOUT REPOSITORY
        # -------------------------------------------------------------
        print(f"[1/4] Setting up repo workspace at {workspace_repo}...")
        if workspace_repo.exists():
            shutil.rmtree(workspace_repo)

        try:
            run_cmd(["git", "clone", repo_url, str(workspace_repo)])
            if base_sha:
                print(f"[+] Checking out base commit: {base_sha}")
                run_cmd(["git", "checkout", base_sha], cwd=workspace_repo)
        except subprocess.CalledProcessError as e:
            print(f"[-] Git setup/checkout failed: {e.stderr}", file=sys.stderr)
            return {"issue": issue_folder_name, "status": "failed", "stage": "git_setup", "error": e.stderr}

        # Inject fail-to-pass test script if available
        if test_script_path:
            dest_test_path = workspace_repo / "tests" / test_script_path.name
            dest_test_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(test_script_path, dest_test_path)
            init_file = dest_test_path.parent / "__init__.py"
            if not init_file.exists():
                init_file.touch()

        # -------------------------------------------------------------
        # BUILD DOCKER IMAGE WITH MINI-SWE-AGENT INSTALLED
        # -------------------------------------------------------------
        sanitized_dockerfile = run_output_dir / "env.dockerfile"
        inject_real_env_keys_and_tools(dockerfile_path, sanitized_dockerfile, workspace_repo=workspace_repo)

        print(f"[2/4] Building Docker image '{image_tag}' with repo context at {workspace_repo}...")
        try:
            run_cmd([
                "docker", "build",
                "-t", image_tag,
                "-f", str(sanitized_dockerfile.resolve()),
                str(workspace_repo.resolve())
            ])
        except subprocess.CalledProcessError as e:
            print(f"[-] Docker build failed: {e.stderr}", file=sys.stderr)
            return {"issue": issue_folder_name, "status": "failed", "stage": "docker_build", "error": e.stderr}

        # -------------------------------------------------------------
        # RUN MINI-SWE-AGENT INSIDE DOCKER CONTAINER
        # -------------------------------------------------------------
        print(f"[3/4] Running mini-swe-agent inside {image_tag} with model={model}...")

        # Forward environment variables and ignore unmapped cost errors
        docker_env_args = [
            "-e", "MSWEA_CONFIGURED=true",
            "-e", "MSWEA_COST_TRACKING=ignore_errors",
        ]

        env_vars_to_pass = [
            "OPENAI_API_KEY",
            "OPENAI_API_BASE",
            "OPENAI_BASE_URL",
            "FORGE_API_KEY",
            "ANTHROPIC_API_KEY",
            "TAVILY_API_KEY",
            "GITHUB_TOKEN",
        ]
        for key in env_vars_to_pass:
            val = os.getenv(key)
            if val:
                docker_env_args.extend(["-e", f"{key}={val}"])

        # Format model string cleanly
        model_name = model
        if not ("/" in model_name):
            model_name = f"openai/{model_name}"

        docker_agent_cmd = [
            "docker", "run", "--rm",
            *docker_env_args,
            "-v", f"{workspace_repo.resolve()}:/app",
            "-v", f"{run_output_dir.resolve()}:/output",
            "-w", "/app",
            image_tag,
            "mini-swe-agent",
            "-c", "mini.yaml",
            "-m", model_name,
            "-y",
            "--exit-immediately",
            "-t", problem_statement,
            "-o", "/output/trajectory.json",
        ]

        try:
            proc = subprocess.run(
                docker_agent_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=TIMEOUT_MINUTES * 60,
            )
            log_file_path.write_text(proc.stdout, encoding="utf-8")
        except subprocess.TimeoutExpired:
            print(f"[-] mini-swe-agent timed out after {TIMEOUT_MINUTES} mins.")
            return {"issue": issue_folder_name, "status": "timeout"}
        except Exception as e:
            print(f"[-] Execution error: {e}")
            return {"issue": issue_folder_name, "status": "failed", "stage": "agent_execution", "error": str(e)}

        # Parse tokens from trajectory and write standardized cost.json
        cost_info = parse_and_calculate_cost(trajectory_file_path, model_name, issue_folder_name)
        cost_file_path.write_text(json.dumps(cost_info, indent=2), encoding="utf-8")
        print(f"[✓] Saved cost.json: ${cost_info['cost_usd']:.4f} ({cost_info['total_tokens']:,} total tokens)")

        # -------------------------------------------------------------
        # EXTRACT GIT DIFF PATCH (INCLUDING UNTRACKED FILES)
        # -------------------------------------------------------------
        print(f"[4/4] Extracting git patch from workspace...")
        run_cmd(["git", "add", "-A", "--intent-to-add"], cwd=workspace_repo, check=False)
        diff_proc = run_cmd(["git", "diff"], cwd=workspace_repo, check=False)
        patch_content = diff_proc.stdout

        if patch_content.strip():
            patch_output_path.write_text(patch_content, encoding="utf-8")
            print(f"[+] Successfully generated and saved patch to: {patch_output_path}")
            result_status = "success"
        else:
            print("[-] No changes / empty diff generated by agent.")
            result_status = "empty_patch"

        return {
            "issue": issue_folder_name,
            "issue_number": issue_num,
            "status": result_status,
            "patch_file": str(patch_output_path) if result_status == "success" else None,
            "log_file": str(log_file_path),
            "cost_file": str(cost_file_path),
            "cost_usd": cost_info["cost_usd"],
        }

    finally:
        # -------------------------------------------------------------
        # CLEANUP: DOCKER IMAGE & REPO WORKSPACE
        # -------------------------------------------------------------
        print(f"[*] Cleaning up workspace for issue #{issue_num}...")
        if workspace_repo.exists():
            shutil.rmtree(workspace_repo, ignore_errors=True)

        try:
            run_cmd(["docker", "rmi", image_tag], check=False)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Batch Runner for mini-swe-agent using issue_*.json problem statements.")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        required=True,
        help="Path to directory containing issue artifact folders (e.g. ./result/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./batch_sweagent_patches"),
        help="Directory to save generated patches and logs.",
    )
    parser.add_argument(
        "--repos-cache",
        type=Path,
        default=Path("./.repos_cache"),
        help="Directory to temporarily clone and work on repos.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="LLM model string for mini-swe-agent.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.repos_cache.mkdir(parents=True, exist_ok=True)

    artifact_folders = [
        p for p in args.artifacts_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]

    print(f"Found {len(artifact_folders)} issue artifact folders to process.")

    summary_results = []
    try:
        for folder in sorted(artifact_folders):
            res = process_single_issue(
                artifact_dir=folder,
                output_base_dir=args.output_dir,
                repos_cache_dir=args.repos_cache,
                model=args.model,
            )
            summary_results.append(res)
    finally:
        if args.repos_cache.exists():
            print("\n[*] Removing top-level repo cache directory...")
            shutil.rmtree(args.repos_cache, ignore_errors=True)

    summary_path = args.output_dir / "batch_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_issues": len(artifact_folders),
                "results": summary_results,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 60)
    print(f"[✓] Batch processing complete. Summary saved to {summary_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()