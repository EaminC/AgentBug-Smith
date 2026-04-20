"""
Quick usage:
1) Default (auto clone ../langchain if missing, auto generate test Dockerfile, then run):
   python exp/docker_test.py
2) Custom repo path:
   python exp/docker_test.py /path/to/langchain
3) Custom repo + dockerfile:
   python exp/docker_test.py /path/to/langchain libs/langchain/test_runner.Dockerfile

Flow: discover candidate tests -> AI ranks/filters for Docker/env relevance (>=5 when possible)
-> loop docker test each file -> print dependency/static lines per step (progress on stderr).
"""

import sys
import subprocess
from pathlib import Path

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from repo.term import log_line, paint  # noqa: E402
from testrun import (  # noqa: E402
    docker_test_repo_test,
    ensure_langchain_test_dockerfile,
    filter_static_dependency_report,
    filter_tests_for_docker_env,
    get_test_file_path,
)

_DEFAULT_LANGCHAIN_REPO = (_AGENTSMITH_ROOT.parent / "langchain").resolve()
_DEFAULT_LANGCHAIN_GIT_URL = "https://github.com/langchain-ai/langchain.git"
_DEFAULT_DOCKERFILE_REL = Path("libs/langchain/test_runner.Dockerfile")

def _banner(title: str, *, stream=sys.stderr) -> None:
    line = "=" * 72
    print(line, file=stream, flush=True)
    print(f"  {title}", file=stream, flush=True)
    print(line, file=stream, flush=True)


if __name__ == "__main__":
    repo_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else _DEFAULT_LANGCHAIN_REPO
    dockerfile_path = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_DOCKERFILE_REL

    log_line("[docker_test]", paint("1;36", "AgentBug-Smith docker_test"), paint("90", str(_AGENTSMITH_ROOT)))
    print(file=sys.stderr, flush=True)

    if not repo_path.exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        _banner("Phase: clone repository (missing locally)", stream=sys.stderr)
        log_line(
            "[docker_test]",
            paint("33", "Cloning"),
            paint("32", str(repo_path)),
            paint("90", "<-"),
            paint("32", _DEFAULT_LANGCHAIN_GIT_URL),
        )
        subprocess.run(
            ["git", "clone", _DEFAULT_LANGCHAIN_GIT_URL, str(repo_path)],
            check=True,
        )
        log_line("[docker_test]", paint("32", "Clone finished."), stream=sys.stderr)
        print(file=sys.stderr, flush=True)

    if len(sys.argv) <= 2:
        _banner("Phase: ensure test Dockerfile template", stream=sys.stderr)
        dockerfile_path = ensure_langchain_test_dockerfile(repo_path, relpath=str(_DEFAULT_DOCKERFILE_REL))
        log_line("[docker_test]", paint("90", "dockerfile →"), paint("32", str(dockerfile_path)))
        print(file=sys.stderr, flush=True)

    _banner("Phase: discover candidate test files (Forge + fallback)", stream=sys.stderr)
    raw_list = get_test_file_path(repo_path)
    if not raw_list:
        log_line("[docker_test]", paint("31", "No candidate test paths found."), stream=sys.stderr)
        raise SystemExit(2)
    log_line("[docker_test]", paint("32", f"{len(raw_list)}"), paint("90", "candidates"))
    preview_n = min(8, len(raw_list))
    for i, p in enumerate(raw_list[:preview_n]):
        log_line("[docker_test]", paint("90", f"  [{i}]"), paint("35", p), stream=sys.stderr)
    if len(raw_list) > preview_n:
        log_line(
            "[docker_test]",
            paint("90", f"  … {len(raw_list) - preview_n} more (omitted)"),
            stream=sys.stderr,
        )
    print(file=sys.stderr, flush=True)

    _banner("Phase: rank / filter for Docker & env (≥5 paths when candidates allow)", stream=sys.stderr)
    log_line("[docker_test]", paint("90", "Calling filter_tests_for_docker_env …"), stream=sys.stderr)
    path_list = filter_tests_for_docker_env(
        repo_path,
        raw_list,
        dockerfile_path=dockerfile_path,
    )
    if not path_list:
        log_line("[docker_test]", paint("31", "No tests left after filter (unexpected)."), stream=sys.stderr)
        raise SystemExit(2)
    log_line(
        "[docker_test]",
        paint("32", f"{len(path_list)}"),
        paint("90", "tests to run"),
        paint("90", f"(from {len(raw_list)} candidates)"),
        stream=sys.stderr,
    )
    for i, p in enumerate(path_list):
        log_line("[docker_test]", paint("90", f"  [{i}]"), paint("36", p), stream=sys.stderr)
    print(file=sys.stderr, flush=True)

    _banner("Phase: docker build (once) + run each test", stream=sys.stderr)
    static_blocks: list[str] = []
    any_fail = False
    for idx, test_rel in enumerate(path_list):
        log_line(
            "[docker_test]",
            paint("1;33", f"Run {idx + 1}/{len(path_list)}"),
            paint("32", test_rel),
            stream=sys.stderr,
        )
        if idx == 0:
            log_line("[docker_test]", paint("90", "  → docker build + run"), stream=sys.stderr)
        else:
            log_line("[docker_test]", paint("90", "  → docker run only (reuse image)"), stream=sys.stderr)

        ok, report = docker_test_repo_test(
            repo_path,
            dockerfile_path,
            test_rel,
            skip_build=(idx > 0),
        )
        if not ok:
            any_fail = True
        static_only = filter_static_dependency_report(report)
        block = f"=== {test_rel} (ok={ok}) ===\n{static_only}"
        static_blocks.append(block)

        # Show static/dep snippet immediately (readable, incremental)
        print(paint("90", "— static / dependency-related lines —"), file=sys.stderr, flush=True)
        for ln in static_only.splitlines():
            print(paint("90", "  | "), file=sys.stderr, end="", flush=True)
            print(ln, file=sys.stderr, flush=True)
        print(file=sys.stderr, flush=True)

    _banner("Summary", stream=sys.stderr)
    summary_parts = [
        paint("32" if not any_fail else "33", "Done."),
        paint("90", f"{len(path_list)} test file(s)."),
    ]
    if any_fail:
        summary_parts.append(paint("31", "Some runs failed (see static lines above)."))
    log_line("[docker_test]", *summary_parts, stream=sys.stderr)
    print(file=sys.stderr, flush=True)

    # Full static-only log on stdout for piping / logs
    print("--- static / dependency-related output (full) ---\n")
    print("\n\n".join(static_blocks))
    raise SystemExit(1 if any_fail else 0)
