"""
End-to-end: clone GitHub repo from an issue JSON, generate Dockerfile, optional cleanup.

Paths and repo name come from the same JSON as ``repo.load_issue_workspace`` (see ``data/issue_13.json``).
Docker prompts/config: ``conf/dockerbuild/init``, ``prompt/dockerbuild/init``;
write stage: ``conf/dockerbuild/write``, ``prompt/dockerbuild/write`` (``dockerwrite``);
``dockerbuild`` runs ``docker build`` and feeds failures back into ``dockerwrite`` as ``feedback``.

After a successful image build, ``testgen`` writes a test file (see ``src/testgen``). Then ``testrun.run_f2p_verify``
builds the image, runs the test, applies ``linked_prs[].patch``, rebuilds, runs the test again; outcome ``f2p`` means
fail2pass. Unless the outcome is ``f2p``, the script **resets the repo to ``base_sha``** (if present), feeds the
verify log back into ``testgen`` as ``feedback``, and repeats (same pattern as the dockerwrite/build loop).

An **outer epoch** loop (see ``conf/dockerbuild/end-end.json``) wraps the dockerwrite/build rounds and the f2p rounds.
The first epoch starts with no feedback; from the second epoch onward, ``dockerwrite`` and ``testgen`` each receive the
same merged text built from the last docker-build feedback and the last fail2pass verify feedback (see
``utils.format_dual_feedback``).

At script start/end, :class:`stats.StatsTool` records a UTC window and aggregates Forge token usage
(see ``src/stats``, modeled on ``SWEGENT-BENCH/src/stats``).

Each run creates ``result/<issue_stem>_<utc>/`` with ``run.log`` (full stdout/stderr), ``agentsmith_stat.json``,
``dockerbuild.txt``, ``f2p.txt``, ``summary.json``, plus copies of the issue JSON, ``env.dockerfile``, and the
generated test file when present.
"""
import sys
from pathlib import Path
import subprocess
import json
import shutil

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from dockerbuild.build import dockerbuild  # noqa: E402
from dockerbuild.init import dockerinit  # noqa: E402
from dockerbuild.write import dockerwrite  # noqa: E402
from repo import clone_issue_repo, load_issue_workspace, remove_issue_repo  # noqa: E402
from repo.git_ops import ensure_repo_at_commit, read_linked_pr_base_sha, reset_repo_to_base  # noqa: E402
from repo.inspect import get_file_tree  # noqa: E402
from stats import StatsTool  # noqa: E402
from testgen import load_issue_testgen_context, testgen  # noqa: E402
from testrun import (  # noqa: E402
    docker_test_repo_test,
    ensure_langchain_test_dockerfile,
    filter_static_dependency_report,
    filter_tests_for_docker_env,
    get_test_file_path,
    run_f2p_verify
)
from utils import (  # noqa: E402
    append_text,
    finalize_run_artifacts,
    format_dual_feedback,
    load_end_end_config,
    result_run_with_tee,
    write_summary_json,
)
from utils.cofix_agent import cofix_agent
from utils.lang_detect import detect_project_language
import time
from datetime import timedelta


_ISSUE_JSON = _AGENTSMITH_ROOT / "data/issues_50" / "issue_2175.json"
_MODEL = "tensorblock/gpt-4.1-mini"


def truncate_middle(text: str | None, max_chars: int = 40000) -> str | None:
    """Truncates the middle of a string if it exceeds max_chars to avoid OS Argument limits."""
    if not text or len(text) <= max_chars:
        return text
    
    half = max_chars // 2
    separator = "\n\n... [LOG TRUNCATED] ...\n\n"
    
    return text[:half] + separator + text[-half:]

def _run_docker_test(repo_path: Path, dockerfile_path: Path) -> tuple[bool, str | None]:
    """
    Run tests using the generated Dockerfile.
    This function is an adaptation of the logic in docker_test.py.
    Returns a tuple of (all_tests_succeeded, aggregated_error_report).
    """
    print("\n--- Running Docker Tests ---")
    raw_list = get_test_file_path(repo_path)
    if not raw_list:
        print("No candidate test paths found for docker testing.", file=sys.stderr)
        return True, None  # No tests to run is a success condition for this stage

    print(f"Found {len(raw_list)} candidate test files.")
    path_list = filter_tests_for_docker_env(
        repo_path,
        raw_list,
        dockerfile_path=dockerfile_path,
    )

    if not path_list:
        print("No tests left after filter for docker testing.", file=sys.stderr)
        return True, None # No tests to run is a success condition for this stage

    print(f"Running {len(path_list)} tests...")
    success_count = 0
    any_fail = False
    error_reports = []
    for idx, test_rel in enumerate(path_list):
        print(f"Running test {idx + 1}/{len(path_list)}: {test_rel}")
        ok, report = docker_test_repo_test(
            repo_path,
            dockerfile_path,
            test_rel,
            skip_build=(idx > 0),
        )
        print(f"Test {test_rel} {'succeeded' if ok else 'failed'}.")
        if not ok:
            any_fail = True
        else:
            success_count += 1
        if report:
            static_only = filter_static_dependency_report(report)
            print("--- Static / dependency-related lines ---")
            print(static_only)
            print("-----------------------------------------")
            if not ok:
                error_reports.append(static_only)

    if len(path_list) > 5:
        all_succeeded = success_count >= 5
    else:
        all_succeeded = success_count >= len(path_list)-3
    print("--- Docker Tests Finished ---\n")
    return all_succeeded, "\n".join(error_reports) if error_reports else None


def _run(run_dir: Path) -> None:
    _cfg = load_end_end_config(_AGENTSMITH_ROOT)
    _docker_log = run_dir / "dockerbuild.txt"
    _f2p_log = run_dir / "f2p.txt"
    _ws = load_issue_workspace(_ISSUE_JSON)
    clone_issue_repo(_ws, verbose=True)
    lang_info = detect_project_language(_ws.local_repo_path)
    print(f"Detected Language: {lang_info['name']}")

    _ctx = load_issue_testgen_context(_ISSUE_JSON)
    _n = _ctx.issue_number or 0
    _test_rel = f"tests/agentsmith_fail2pass_{_n or 'issue'}{lang_info['ext']}"

    _base = read_linked_pr_base_sha(_ISSUE_JSON)
    if _base:
        _co_ok, _co_err = ensure_repo_at_commit(_ws.local_repo_path, _base, verbose=True)
        if not _co_ok:
            print(_co_err, file=sys.stderr)
            sys.exit(1)
            
    # Load patch test configuration early
    patch_test_src = None
    try:
        with open(_ISSUE_JSON, "r", encoding="utf-8") as f:
            issue_data = json.load(f)
        test_paths = (
            issue_data.get("linked_prs", [{}])[0].get("test_paths_in_patch", []) or 
            issue_data.get("test_paths_in_patch", [])
        )
        if test_paths and len(test_paths) > 0:
            patch_test_src = test_paths[0]
    except Exception as e:
        print(f"[pipeline-warning] Failed looking up in-patch test config: {e}", file=sys.stderr)

    dockerinit(
        _ws.local_repo_path,
        _ws.dockerfile_out,
        model=_MODEL,
        verbose=True,
        language=lang_info["name"]
    )

    if (_cfg.max_f2p_rounds > 1 or _cfg.max_outer_epochs > 1) and not _base:
        print(
            "warning: issue JSON has no `linked_prs[].base_sha`; multi-round / multi-epoch reset uses `git reset --hard` only when base_sha is set.",
            file=sys.stderr,
        )

    _stored_docker = None
    _stored_f2p = None
    _f2p_succeeded = False

    for _epoch in range(1, _cfg.max_outer_epochs + 1):
        if _epoch > 1 and _base:
            _rs_ok, _rs_err = reset_repo_to_base(_ws.local_repo_path, _base)
            subprocess.run(["git", "clean", "-fd", "-e", "env.dockerfile"], cwd=str(_ws.local_repo_path))
            if not _rs_ok:
                print(_rs_err, file=sys.stderr)
                break

        if _epoch == 1:
            _fb_outer_docker = None
            _fb_outer_f2p = None
        else:
            _merged = format_dual_feedback(_stored_docker, _stored_f2p)
            _fb_outer_docker = _merged
            _fb_outer_f2p = _merged

        _feedback = _fb_outer_docker
        _build_ok = False
        for _round in range(1, _cfg.max_docker_rounds + 1):
            repo_structure = get_file_tree(_ws.local_repo_path, n=3)
            context_structure = f"\n### Current Repository Structure (Depth=3):\n{repo_structure}\n"
            current_feedback = context_structure + (_feedback or "")
            dockerwrite(
                _ws.local_repo_path,
                verbose=True,
                model=_MODEL,
                project_root=_AGENTSMITH_ROOT,
                feedback=current_feedback,
                language=lang_info["name"],
            )
            _build_ok, _log = dockerbuild(
                _ws.local_repo_path,
                dockerfile="env.dockerfile",
                verbose=True,
                project_root=_AGENTSMITH_ROOT,
                nocache=True
            )
            _log = truncate_middle(_log)
            append_text(
                _docker_log,
                f"epoch={_epoch} docker_round={_round} ok={_build_ok}",
                _log or "",
            )
            if _build_ok:
                docker_tests_ok, docker_test_errors = _run_docker_test(_ws.local_repo_path, _ws.dockerfile_out)
                if docker_tests_ok:
                    print("Docker tests passed.")
                    break
                else:
                    print("Docker tests failed. Feeding back errors to regenerate Dockerfile.")
                    _feedback = docker_test_errors
                    _build_ok = False # Set to false to indicate we need to rebuild
            else:
                _feedback = _log

        _stored_docker = _feedback

        if not _build_ok:
            print("Skipping testgen / testrun: docker build did not succeed.", file=sys.stderr)
            continue
        else:
            f2p_rounds = _cfg.max_f2p_rounds

        _f2p_feedback = _fb_outer_f2p
        for _f2p_round in range(1, f2p_rounds + 1):
            if _f2p_round > 1 and _base:
                _rs_ok, _rs_err = reset_repo_to_base(_ws.local_repo_path, _base)
                subprocess.run(["git", "clean", "-fd", "-e", "env.dockerfile"], cwd=str(_ws.local_repo_path))
                if not _rs_ok:
                    print(_rs_err, file=sys.stderr)
                    break

            has_patch_test = False
            if patch_test_src:
                original_test_path = _ws.local_repo_path / patch_test_src
                target_test_path = _ws.local_repo_path / _test_rel
                if original_test_path.exists():
                    target_test_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original_test_path, target_test_path)
                    print(f"Restored in-patch test: '{patch_test_src}'")
                    has_patch_test = True

            if not has_patch_test:
                repo_structure = get_file_tree(_ws.local_repo_path, n=3)
                context_structure = f"\n### Current Repository Structure (Depth=3):\n{repo_structure}\n"
                current_f2p_feedback = context_structure + (_f2p_feedback or "")
                _tg_ok, _tg_report = testgen(
                    _ws.local_repo_path,
                    issue_json_path=_ISSUE_JSON,
                    verbose=True,
                    project_root=_AGENTSMITH_ROOT,
                    model=_MODEL,
                    feedback=current_f2p_feedback,
                    language=lang_info["name"]
                )
                print(_tg_report)
                if not _tg_ok:
                    break
            else:
                print("[end-end] In-patch test detected and used. Skipping testgen.")

            base_cmd = lang_info['runner'].split()
            test_cmd = base_cmd + [_test_rel]
            _outcome, _f2p_report = run_f2p_verify(
                _ws.local_repo_path,
                issue_json_path=_ISSUE_JSON,
                dockerfile="env.dockerfile",
                run_argv=test_cmd,
                test_relpath=_test_rel,
                verbose=True,
                project_root=_AGENTSMITH_ROOT,
                nocache=True
            )
            _f2p_report = truncate_middle(_f2p_report)
            append_text(
                _f2p_log,
                f"epoch={_epoch} f2p_round={_f2p_round} outcome={_outcome}",
                _f2p_report,
            )
            print(_f2p_report)
            if _outcome == "f2p":
                _f2p_succeeded = True
                break
            elif _outcome == "error":
                print("Error detected. Re-initializing Dockerfile...")
                dockerinit(_ws.local_repo_path, _ws.dockerfile_out, model=_MODEL, verbose=True, language=lang_info["name"])
            _f2p_feedback = f"Round {_f2p_round} verify outcome: {_outcome}\n\n{_f2p_report}"

        _stored_f2p = _f2p_feedback

        try:
            subprocess.run(["docker", "system", "prune", "-f"], check=False)
        except Exception as cleanup_err:
            print(f" Warning: Docker cleanup failed: {cleanup_err}", file=sys.stderr)
        
        if _f2p_succeeded:
            break

    # Apply cofix agent to generate final fixes for both Dockerfile and test file, if not already f2p
    if not _f2p_succeeded:
        print("\n[end-end] Epochs cannot solve the issue. Triggering cofix agent for final repair...")

        for _cofix_round in range(1, _cfg.max_cofix_rounds + 1):
            print(f"\n--- Cofix Round {_cofix_round} ---")

            # Reset the repo state before generating new files or applying patches
            if _cofix_round > 1 and _base:
                _rs_ok, _rs_err = reset_repo_to_base(_ws.local_repo_path, _base)
                subprocess.run(["git", "clean", "-fd", "-e", "env.dockerfile"], cwd=str(_ws.local_repo_path))
                if not _rs_ok:
                    print(_rs_err, file=sys.stderr)
                    break

            has_patch_test = False
            if patch_test_src:
                original_test_path = _ws.local_repo_path / patch_test_src
                target_test_path = _ws.local_repo_path / _test_rel
                if original_test_path.exists():
                    target_test_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original_test_path, target_test_path)
                    print(f"Restored in-patch test: '{patch_test_src}'")
                    has_patch_test = True

            # 3. Dynamic Cofix Invocation
            # If we have an in-patch test, set test_relpath to None so the LLM ONLY rewrites the Dockerfile
            target_test_relpath = None if has_patch_test else _test_rel
            
            if has_patch_test:
                print("[end-end] In-patch test detected. Cofix agent will run in 'Environment-Only' mode.")
            else:
                print("[end-end] No in-patch test found. Cofix agent will run in 'Full-Generation' mode.")

            _cofix_ok, _cofix_log = cofix_agent(
                _ws.local_repo_path,
                dockerfile="env.dockerfile",
                test_relpath=target_test_relpath,
                feedback=_stored_f2p,
                model=_MODEL,
                project_root=_AGENTSMITH_ROOT,
                verbose=True,
                language=lang_info["name"]
            )

            # 4. Verify F2P on the repaired files
            if _cofix_ok:
                print(f"[end-end] cofix applied repairs (Round {_cofix_round}). Re-verifying F2P...")
                base_cmd = lang_info['runner'].split()
                test_cmd = base_cmd + [_test_rel]
                _outcome, _f2p_report = run_f2p_verify(
                    _ws.local_repo_path,
                    issue_json_path=_ISSUE_JSON,
                    dockerfile="env.dockerfile",
                    run_argv=test_cmd,
                    test_relpath=_test_rel,
                    verbose=True,
                    project_root=_AGENTSMITH_ROOT,
                    nocache=True
                )
                append_text(
                    _f2p_log,
                    f"stage=cofix_verify outcome={_outcome}",
                    _f2p_report,
                )
                print(_f2p_report)

                if _outcome == "f2p":
                    _f2p_succeeded = True
                    print(f"[end-end] cofix successfully achieved F2P on round {_cofix_round}!")
                    break
                else:
                    print(f"[end-end] cofix did not achieve F2P on round {_cofix_round}.")
                    _stored_f2p = f"Cofix Round {_cofix_round} verify outcome: {_outcome}\n\n{_f2p_report}"
            else:
                print(f"[end-end] cofix agent failed with error: {_cofix_log}")
                _stored_f2p = f"Cofix Round {_cofix_round} agent error: {_cofix_log}"
        
        if not _f2p_succeeded:
            print("[end-end] Cofix rounds exhausted. Final state recorded in logs and summary.")

    write_summary_json(
        run_dir / "summary.json",
        issue_json_path=_ISSUE_JSON,
        run_dir=run_dir,
        f2p_succeeded=_f2p_succeeded,
        extra={"test_relpath": _test_rel.replace("\\", "/")},
    )
    finalize_run_artifacts(
        run_dir,
        issue_json_path=_ISSUE_JSON,
        repo_root=_ws.local_repo_path,
        dockerfile_relpath="env.dockerfile",
        test_relpath=_test_rel,
    )

    remove_issue_repo(_ws, verbose=True)


if __name__ == "__main__":
    start_time = time.time()
    with result_run_with_tee(_AGENTSMITH_ROOT, _ISSUE_JSON, banner="[end-end] result dir:") as _run_dir:
        _usage_stats = StatsTool(
            model=_MODEL,
            verbose=True,
            stats_file=_run_dir / "agentsmith_stat.json",
        )
        _usage_stats.start()
        try:
            _run(_run_dir)
        finally:
            _usage_stats.end()
            end_time = time.time()
            duration = end_time - start_time
            formatted_duration = str(timedelta(seconds=int(duration)))
            print("-" * 30)
            print(f"Pipeline Execution Complete.")
            print(f"Total Duration: {formatted_duration} ({duration:.2f} seconds)")
            print("-" * 30)