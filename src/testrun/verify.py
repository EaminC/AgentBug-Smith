"""
Fail2pass **verification** in Docker: build → run test → ``git apply`` patch → rebuild → run test.

Outcome codes (aligned with ``f2p.py`` semantics, shortened for callers):

- ``f2p`` — first run test exit ≠ 0, second run exit 0 (fail2pass).
- ``f2f`` — both non-zero.
- ``p2p`` — both zero.
- ``p2f`` — first zero, second non-zero.
- ``error`` — build/apply/docker failure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dockerbuild.build import dockerbuild  # noqa: E402
from repo.git_ops import git_apply_patch  # noqa: E402
from repo.term import log_line, paint  # noqa: E402
from testgen import load_issue_testgen_context  # noqa: E402


def _docker_image_tag(repo_root: Path) -> str:
    return f"test-build-{repo_root.resolve().name.lower()}"


def _last_workdir_in_dockerfile(dockerfile: Path) -> Optional[str]:
    if not dockerfile.is_file():
        return None
    last: Optional[str] = None
    try:
        for raw in dockerfile.read_text(encoding="utf-8", errors="replace").splitlines():
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if s.upper().startswith("WORKDIR "):
                rest = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
                last = rest.strip().strip('"').strip("'") or last
    except OSError:
        return last
    return last


def _docker_run(
    repo_root: Path,
    image_tag: str,
    argv: List[str],
    *,
    platform: str = "linux/amd64",
    workdir: Optional[str] = None,
    timeout: int = 600,
) -> Tuple[int, str]:
    cmd: List[str] = ["docker", "run", "--rm", "--platform", platform]
    if workdir:
        cmd.extend(["-w", workdir])
    cmd.append(image_tag)
    cmd.extend(argv)
    try:
        r = subprocess.run(
            cmd,
            cwd=str(repo_root.resolve()),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "docker run: timeout"
    except OSError as e:
        return 1, f"docker run failed: {e}"


def _classify(rc1: int, rc2: int) -> str:
    p1 = rc1 == 0
    p2 = rc2 == 0
    if not p1 and p2:
        return "f2p"
    if not p1 and not p2:
        return "f2f"
    if p1 and p2:
        return "p2p"
    return "p2f"


def run_f2p_verify(
    repo_root: Path | str,
    issue_json_path: Path | str,
    *,
    dockerfile: str = "env.dockerfile",
    project_root: Optional[Path] = None,
    test_relpath: Optional[str] = None,
    run_argv: Optional[List[str]] = None,
    image_workdir: Optional[str] = None,
    platform: str = "linux/amd64",
    verbose: bool = False,
) -> Tuple[str, str]:
    """
    1. ``docker build`` (buggy tree + generated test).
    2. Run test command → ``rc1`` (pytest / test runner exit code in container).
    3. ``git apply`` patch from issue JSON.
    4. ``docker build`` again.
    5. Run same test → ``rc2``.

    Returns ``(outcome, report)`` where ``outcome`` is ``f2p`` | ``f2f`` | ``p2p`` | ``p2f`` | ``error``.
    """
    root = Path(project_root or PROJECT_ROOT).resolve()
    rroot = Path(repo_root).resolve()
    ctx = load_issue_testgen_context(issue_json_path)

    if not ctx.patch.strip():
        return "error", "No `linked_prs[].patch` in issue JSON; cannot verify fail2pass."

    n = ctx.issue_number or 0
    rel = test_relpath or f"tests/agentsmith_fail2pass_{n or 'issue'}.py"
    rel = rel.strip().replace("\\", "/")

    df = rroot / dockerfile
    wd = image_workdir if image_workdir is not None else _last_workdir_in_dockerfile(df)
    if run_argv is None:
        run_argv = ["python", "-m", "pytest", "-q", rel]

    image_tag = _docker_image_tag(rroot)
    lines: List[str] = []

    def _v(msg: str) -> None:
        lines.append(msg)
        if verbose:
            print(paint("90", msg), file=sys.stderr)

    if verbose:
        print(paint("1;36", "\n========== testrun / fail2pass verify =========="), file=sys.stderr)
        log_line("[testrun]", paint("90", "repo:"), paint("32", str(rroot)))
        log_line("[testrun]", paint("90", "test file:"), paint("36", rel))

    _v("--- Phase A: docker build (before patch) ---")
    ok_b, log_b = dockerbuild(
        rroot,
        dockerfile=dockerfile,
        project_root=root,
        verbose=verbose,
        platform=platform,
    )
    if not ok_b:
        return "error", "Docker build (before patch) failed:\n" + log_b[-12_000:]

    _v("--- Phase B: run test in container (expect failure for fail2pass) ---")
    rc1, out1 = _docker_run(rroot, image_tag, run_argv, platform=platform, workdir=wd)
    _v(f"test command exit code: {rc1}")

    _v("--- Phase C: git apply patch ---")
    gok, gerr = git_apply_patch(rroot, ctx.patch)
    if not gok:
        return "error", f"git apply failed:\n{gerr}"

    _v("--- Phase D: docker build (after patch) ---")
    ok_a, log_a = dockerbuild(
        rroot,
        dockerfile=dockerfile,
        project_root=root,
        verbose=verbose,
        platform=platform,
    )
    if not ok_a:
        return "error", "Docker build (after patch) failed:\n" + log_a[-12_000:]

    _v("--- Phase E: run test in container (expect pass for fail2pass) ---")
    rc2, out2 = _docker_run(rroot, image_tag, run_argv, platform=platform, workdir=wd)
    _v(f"test command exit code: {rc2}")

    outcome = _classify(rc1, rc2)
    report_lines = list(lines)
    report_lines.append(f"\noutcome={outcome} (rc1={rc1}, rc2={rc2})")
    report_lines.append("\n--- first test run (tail) ---\n" + out1[-8000:])
    report_lines.append("\n--- second test run (tail) ---\n" + out2[-8000:])
    report = "\n".join(report_lines)

    if verbose:
        log_line("[testrun]", paint("90", "result:"), paint("36", outcome))
        print(paint("1;36", "================================================\n"), file=sys.stderr)

    return outcome, report


__all__ = ["run_f2p_verify"]
