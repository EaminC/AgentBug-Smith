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
import re
import ast
import json
import shutil
import subprocess
import argparse
import tomllib
from pathlib import Path
from datetime import datetime, timezone


# ==========================================
# Diff & AST Localization Extraction Utils
# ==========================================

def parse_patch_files_and_hunks(patch_text: str) -> dict[str, list[dict]]:
    """
    Parses a unified diff string and extracts modified file paths and line ranges.
    Returns: { file_path: [ { "old_start": int, "old_count": int, "hunk_header": str } ] }
    """
    files_hunks = {}
    current_file = None
    
    # Matches: diff --git a/src/module.py b/src/module.py
    diff_file_pattern = re.compile(r"^diff --git a/(.+?) b/(.+?)$")
    # Matches: @@ -old_start,old_count +new_start,new_count @@ optional_func_header
    hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")

    for line in patch_text.splitlines():
        file_match = diff_file_pattern.match(line)
        if file_match:
            current_file = file_match.group(2)
            if current_file not in files_hunks:
                files_hunks[current_file] = []
            continue
        
        if current_file:
            hunk_match = hunk_pattern.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                header = hunk_match.group(5).strip()
                files_hunks[current_file].append({
                    "old_start": old_start,
                    "old_count": old_count,
                    "hunk_header": header
                })
                
    return files_hunks


def extract_functions_from_ast(py_source: str) -> list[dict]:
    """
    Parses Python source code and extracts function/method line spans.
    Returns: [ { "name": "Class.method" or "func", "start_line": int, "end_line": int } ]
    """
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return []

    functions = []

    def visit_node(node, parent_class=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = f"{parent_class}.{child.name}" if parent_class else child.name
                end_line = getattr(child, "end_lineno", child.lineno)
                functions.append({
                    "name": func_name,
                    "start_line": child.lineno,
                    "end_line": end_line
                })
                visit_node(child, parent_class=func_name)
            elif isinstance(child, ast.ClassDef):
                visit_node(child, parent_class=child.name)

    visit_node(tree)
    return functions


def extract_modified_functions(workspace_repo: Path, patch_text: str) -> set[str]:
    """
    Maps modified lines in the diff back to function names in the workspace repository.
    Returns a set of identifiers formatted as "filepath::FunctionName".
    """
    modified_functions = set()
    files_hunks = parse_patch_files_and_hunks(patch_text)

    for rel_file, hunks in files_hunks.items():
        file_path = workspace_repo / rel_file
        
        if file_path.suffix == ".py" and file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                ast_funcs = extract_functions_from_ast(content)
                
                for hunk in hunks:
                    h_start = hunk["old_start"]
                    h_end = h_start + max(1, hunk["old_count"]) - 1
                    
                    matched = False
                    for f in ast_funcs:
                        # Check overlap between hunk range and function span
                        if not (h_end < f["start_line"] or h_start > f["end_line"]):
                            modified_functions.add(f"{rel_file}::{f['name']}")
                            matched = True
                    
                    # Fallback to hunk header signature if AST overlap finds no function
                    if not matched and hunk["hunk_header"]:
                        clean_hdr = hunk["hunk_header"].split("(")[0].strip()
                        if clean_hdr.startswith("def ") or clean_hdr.startswith("class "):
                            clean_hdr = clean_hdr.split(" ")[1]
                        if clean_hdr:
                            modified_functions.add(f"{rel_file}::{clean_hdr}")
            except Exception:
                pass
        else:
            # Fallback for non-python files or missing files: use hunk headers
            for hunk in hunks:
                if hunk["hunk_header"]:
                    modified_functions.add(f"{rel_file}::{hunk['hunk_header']}")
                else:
                    modified_functions.add(f"{rel_file}::<module>")

    return modified_functions


def calculate_metrics(predicted: set, ground_truth: set) -> dict:
    """Computes Precision, Recall, F1, and Binary Hit for set-based localization."""
    if not ground_truth and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "hit": 1}
    if not predicted:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "hit": 0}
    if not ground_truth:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "hit": 0}

    intersection = predicted.intersection(ground_truth)
    precision = len(intersection) / len(predicted)
    recall = len(intersection) / len(ground_truth)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    hit = 1 if len(intersection) > 0 else 0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "hit": hit
    }


# ==========================================
# Build, Environment & Execution Utilities
# ==========================================

def get_normalized_package_name(workspace_repo: Path) -> str | None:
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

    if workspace_repo and workspace_repo.exists():
        pkg_name = get_normalized_package_name(workspace_repo)
        if pkg_name:
            injected_flags.append(f'ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_{pkg_name}="0.0.1.dev0"')

    injected_flags.append("# -----------------------------------------------------\n")
    
    lines = []
    from_found = False
    for line in content.splitlines():
        replaced = False
        for env_var, real_val in key_mappings.items():
            if line.strip().startswith(f"ENV {env_var}=") or line.strip().startswith(f'ENV "{env_var}"='):
                lines.append(f'ENV {env_var}="{real_val}"')
                replaced = True
                break
        
        if not replaced:
            lines.append(line)

        if not from_found and line.strip().upper().startswith("FROM "):
            lines.extend(injected_flags)
            from_found = True

    if not from_found:
        lines = injected_flags + lines

    output_dockerfile_path.write_text("\n".join(lines), encoding="utf-8")


def run_test_in_container(
    image_tag: str,
    workspace_repo: Path,
    relative_test_path: str,
    timeout_seconds: int = 300
) -> tuple[int, str]:
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
        return -1, "Test execution timed out inside container."
    except Exception as e:
        return -2, f"Failed to execute test container: {str(e)}"


def get_patch_content(
    patch_mode: str,
    issue_data: dict,
    custom_patches_dir: Path | None,
    issue_folder_name: str
) -> tuple[str, str]:
    """Extracts raw patch text according to the selected mode."""
    if patch_mode == "issue_json":
        linked_prs = issue_data.get("linked_prs", [])
        if not linked_prs or not linked_prs[0].get("patch"):
            return "", "No patch found inside linked_prs in issue JSON."
        return linked_prs[0]["patch"], ""

    elif patch_mode == "generated_diff":
        if not custom_patches_dir:
            return "", "--custom-patches-dir must be specified when using 'generated_diff' mode."
        
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
            return "", f"Could not find patch diff in {custom_patches_dir} for {issue_folder_name}."
        
        return patch_file.read_text(encoding="utf-8"), ""

    return "", "Invalid patch mode"


def apply_patch_text(workspace_repo: Path, patch_content: str) -> tuple[bool, str]:
    if not patch_content.strip():
        return False, "Patch content is empty."

    normalized_patch = (
        patch_content.replace("\u00a0", " ")
                     .replace("\u200b", "")
                     .replace("\r\n", "\n")
    )

    temp_patch_path = workspace_repo / "temp_eval_patch.diff"
    temp_patch_path.write_text(normalized_patch, encoding="utf-8")

    apply_proc = run_cmd(
        ["git", "apply", "--ignore-space-change", "--ignore-whitespace", "--whitespace=nowarn", str(temp_patch_path.name)],
        cwd=workspace_repo,
        check=False
    )

    if apply_proc.returncode != 0:
        apply_proc = run_cmd(
            ["git", "apply", "-3", "--ignore-space-change", "--ignore-whitespace", "--whitespace=nowarn", str(temp_patch_path.name)],
            cwd=workspace_repo,
            check=False
        )

    if apply_proc.returncode != 0:
        apply_proc = run_cmd(
            ["patch", "-p1", "--ignore-whitespace", "-f", "-i", str(temp_patch_path.name)],
            cwd=workspace_repo,
            check=False
        )

    temp_patch_path.unlink(missing_ok=True)
    if apply_proc.returncode != 0:
        return False, f"Git apply failed:\n{apply_proc.stderr or apply_proc.stdout}"

    return True, "Patch successfully applied."


# ==========================================
# Single Artifact Evaluation
# ==========================================

def evaluate_single_artifact(
    artifact_dir: Path,
    output_base_dir: Path,
    repos_cache_dir: Path,
    patch_mode: str,
    custom_patches_dir: Path | None
) -> dict:
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
    gt_patch = linked_prs[0].get("patch", "") if linked_prs else ""

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
        # STEP 1: CLONE & CHECKOUT
        print(f"[1/6] Cloning repo and checking out base commit ({base_sha})...")
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

        # STEP 2: FAULT LOCALIZATION ANALYSIS (File & Function Level)
        print(f"[2/6] Computing File-Level and Function-Level Localization...")
        gen_patch, err_msg = get_patch_content(patch_mode, issue_data, custom_patches_dir, issue_folder_name)
        
        gt_files = set(parse_patch_files_and_hunks(gt_patch).keys())
        gen_files = set(parse_patch_files_and_hunks(gen_patch).keys()) if gen_patch else set()

        file_metrics = calculate_metrics(gen_files, gt_files)

        gt_funcs = extract_modified_functions(workspace_repo, gt_patch)
        gen_funcs = extract_modified_functions(workspace_repo, gen_patch) if gen_patch else set()

        func_metrics = calculate_metrics(gen_funcs, gt_funcs)

        print(f"    -> File Loc  : Precision={file_metrics['precision']}, Recall={file_metrics['recall']}, Hit={file_metrics['hit']}")
        print(f"    -> Func Loc  : Precision={func_metrics['precision']}, Recall={func_metrics['recall']}, Hit={func_metrics['hit']}")

        # STEP 3: BUILD DOCKER ENVIRONMENT
        print(f"[3/6] Building Docker environment '{image_tag}'...")
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
            return {
                "issue": issue_folder_name,
                "verdict": "ERROR",
                "reason": "docker_build_failed",
                "file_localization": file_metrics,
                "function_localization": func_metrics,
                "details": e.stderr
            }

        # STEP 4: RUN TEST ON BUGGY REPO (MUST FAIL)
        print(f"[4/6] Verifying FAIL state on buggy commit...")
        fail_code, fail_output = run_test_in_container(image_tag, workspace_repo, relative_test_path)
        fail_log_path.write_text(fail_output, encoding="utf-8")

        if fail_code == 0:
            print("[-] FAIL Verification Failed: Test unexpectedly passed on base commit.")
            return {
                "issue": issue_folder_name,
                "verdict": "FAIL_VERIFICATION_FAILED",
                "reason": "Test unexpectedly passed on base commit (No bug detected).",
                "file_localization": file_metrics,
                "function_localization": func_metrics
            }
        print("[+] Test successfully FAILED on base commit as expected.")

        # STEP 5: APPLY PATCH
        print(f"[5/6] Applying patch using mode '{patch_mode}'...")
        if not gen_patch:
            print(f"[-] Patch retrieval failed: {err_msg}")
            return {
                "issue": issue_folder_name,
                "verdict": "PATCH_APPLY_FAILED",
                "reason": err_msg,
                "file_localization": file_metrics,
                "function_localization": func_metrics
            }

        applied_ok, apply_msg = apply_patch_text(workspace_repo, gen_patch)
        if not applied_ok:
            print(f"[-] Patch application failed: {apply_msg}")
            return {
                "issue": issue_folder_name,
                "verdict": "PATCH_APPLY_FAILED",
                "reason": apply_msg,
                "file_localization": file_metrics,
                "function_localization": func_metrics
            }

        # STEP 6: RUN TEST ON PATCHED REPO (MUST PASS)
        print(f"[6/6] Verifying PASS state on patched codebase...")
        pass_code, pass_output = run_test_in_container(image_tag, workspace_repo, relative_test_path)
        pass_log_path.write_text(pass_output, encoding="utf-8")

        if pass_code != 0:
            print("[-] PASS Verification Failed: Test failed after patch applied.")
            return {
                "issue": issue_folder_name,
                "verdict": "PASS_VERIFICATION_FAILED",
                "reason": "Test still failing after patch applied.",
                "file_localization": file_metrics,
                "function_localization": func_metrics
            }

        print("[✓] SUCCESS: Verified Fail-to-Pass (F2P) reproducibility.")
        return {
            "issue": issue_folder_name,
            "verdict": "F2P_SUCCESS",
            "base_sha": base_sha,
            "test_file": relative_test_path,
            "file_localization": file_metrics,
            "function_localization": func_metrics,
            "gt_files": list(gt_files),
            "gen_files": list(gen_files),
            "gt_functions": list(gt_funcs),
            "gen_functions": list(gen_funcs)
        }

    finally:
        print(f"[*] Cleaning up workspace and image for {issue_folder_name}...")
        if workspace_repo.exists():
            shutil.rmtree(workspace_repo, ignore_errors=True)
        try:
            run_cmd(["docker", "rmi", image_tag], check=False)
        except Exception:
            pass


# ==========================================
# Main CLI & Aggregator
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate Fail-to-Pass (F2P) behavior and Fault Localization across SWE issue artifacts.")
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

    # Compile Summary Metrics
    total = len(results)
    success_count = sum(1 for r in results if r.get("verdict") == "F2P_SUCCESS")
    
    # Macro-averaged Localization Metrics
    file_precisions = [r["file_localization"]["precision"] for r in results if "file_localization" in r]
    file_recalls = [r["file_localization"]["recall"] for r in results if "file_localization" in r]
    file_hits = [r["file_localization"]["hit"] for r in results if "file_localization" in r]

    func_precisions = [r["function_localization"]["precision"] for r in results if "function_localization" in r]
    func_recalls = [r["function_localization"]["recall"] for r in results if "function_localization" in r]
    func_hits = [r["function_localization"]["hit"] for r in results if "function_localization" in r]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": total,
        "f2p_success_count": success_count,
        "f2p_success_rate": f"{(success_count / total * 100):.2f}%" if total else "0%",
        "aggregate_localization": {
            "file_level": {
                "macro_precision": round(sum(file_precisions) / len(file_precisions), 4) if file_precisions else 0.0,
                "macro_recall": round(sum(file_recalls) / len(file_recalls), 4) if file_recalls else 0.0,
                "hit_rate": round(sum(file_hits) / len(file_hits), 4) if file_hits else 0.0
            },
            "function_level": {
                "macro_precision": round(sum(func_precisions) / len(func_precisions), 4) if func_precisions else 0.0,
                "macro_recall": round(sum(func_recalls) / len(func_recalls), 4) if func_recalls else 0.0,
                "hit_rate": round(sum(func_hits) / len(func_hits), 4) if func_hits else 0.0
            }
        },
        "results": results
    }

    summary_file = args.output_dir / "f2p_eval_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"[✓] Evaluation Complete!")
    print(f"[✓] F2P Resolution Rate : {summary['f2p_success_rate']} ({success_count}/{total})")
    print(f"[✓] File Loc Hit Rate   : {summary['aggregate_localization']['file_level']['hit_rate'] * 100:.2f}%")
    print(f"[✓] Func Loc Hit Rate   : {summary['aggregate_localization']['function_level']['hit_rate'] * 100:.2f}%")
    print(f"[✓] Summary written to   : {summary_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()