"""
Run ``docker build`` for a Dockerfile inside a repo (no LLM). Returns success + log text
for passing to :func:`dockerbuild.write.dockerwrite` as ``feedback`` on failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from repo.term import log_line, paint


def _docker_unavailable_hint(detail: str) -> str:
    """Extra help when ``docker ps`` fails (daemon down, socket missing, etc.)."""
    d = detail.lower()
    if "cannot connect" in d or "docker daemon" in d or "is the docker daemon running" in d:
        lines = [
            "The Docker daemon is not reachable (engine not running or socket wrong).",
            "",
            "macOS: open **Docker Desktop** from Applications and wait until the whale icon is idle, then retry `docker ps`.",
            "Linux: e.g. `sudo systemctl start docker` (and ensure your user can access the socket, or use `sudo`).",
            "",
        ]
        return "\n".join(lines)
    return ""


def check_docker_permission() -> Tuple[bool, Optional[str]]:
    """Return (accessible, error_message)."""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, None
        combined = (result.stderr or "") + (result.stdout or "")
        err = combined.lower()
        if "permission denied" in err or "dial unix" in err:
            return False, "Docker permission denied. User may not be in docker group."
        return False, f"Docker check failed: {combined.strip()[:500]}"
    except FileNotFoundError:
        return False, "Docker command not found. Please install Docker."
    except subprocess.TimeoutExpired:
        return False, "Docker check timed out."
    except OSError as e:
        return False, f"Error checking Docker: {e}"


def dockerbuild(
    repo_root: Path | str,
    *,
    dockerfile: str = "env.dockerfile",
    project_root: Optional[Path] = None,
    verbose: bool = False,
    platform: str = "linux/amd64",
    build_timeout: int = 600,
    max_network_retries: int = 3,
) -> Tuple[bool, str]:
    """
    Build ``dockerfile`` inside ``repo_root`` (context = repo root).

    Returns ``(True, combined_output)`` on success, or ``(False, combined_output_or_error)``
    on failure. The second value is suitable for ``dockerwrite(..., feedback=...)``.

    Mirrors SWEGENT-BENCH ``build_docker_image``: permission check, ``docker build -f``,
    network retry with backoff, combined stdout/stderr capture.
    """
    rroot = Path(repo_root).resolve()
    dockerfile_path = rroot / dockerfile

    def _v(msg: str) -> None:
        if verbose:
            print(msg, file=sys.stderr)

    if verbose:
        print(paint("1;36", "\n========== dockerbuild (`docker build`) =========="), file=sys.stderr)
        log_line(
            "[dockerbuild]",
            paint("90", "note:"),
            paint("90", "no LLM prompt here — this step only runs the Docker engine"),
        )
        if project_root is not None:
            log_line(
                "[dockerbuild]",
                paint("90", "project root (ref):"),
                paint("32", str(Path(project_root).resolve())),
            )
        log_line("[dockerbuild]", paint("90", "repo (context):"), paint("32", str(rroot)))
        log_line("[dockerbuild]", paint("90", "dockerfile (-f):"), paint("32", str(dockerfile_path)))
        log_line("[dockerbuild]", paint("90", "platform:"), paint("36", platform))

    ok_perm, perm_err = check_docker_permission()
    if not ok_perm:
        err = f"Docker is not accessible: {perm_err}\n\n"
        if perm_err and (
            "permission denied" in perm_err.lower() or "docker group" in perm_err.lower()
        ):
            err += (
                "SOLUTION:\n"
                "1. sudo usermod -aG docker $USER\n"
                "2. newgrp docker  # or log out and back in\n"
                "3. docker ps\n"
            )
        else:
            err += "Please ensure Docker is installed and running.\n"
            hint = _docker_unavailable_hint(perm_err or "")
            if hint:
                err += "\n" + hint
        _v(paint("31", err))
        if verbose:
            print(paint("1;36", "==============================================\n"), file=sys.stderr)
        return False, err

    if not dockerfile_path.is_file():
        msg = f"Dockerfile not found: {dockerfile_path}"
        _v(paint("31", msg))
        if verbose:
            print(paint("1;36", "==============================================\n"), file=sys.stderr)
        return False, msg

    image_name = f"test-build-{rroot.name.lower()}"
    cmd: List[str] = [
        "docker",
        "build",
        "--platform",
        platform,
        "-f",
        str(dockerfile_path),
        "-t",
        image_name,
        str(rroot),
    ]

    if verbose:
        log_line("[dockerbuild]", paint("90", "image tag (-t):"), paint("36", image_name))
        print(paint("34", "---------- command ----------"), file=sys.stderr)
        print(paint("90", " ".join(cmd)), file=sys.stderr)
        print(paint("34", "---------- docker build ----------"), file=sys.stderr)

    retry_count = 0
    result: Optional[subprocess.CompletedProcess[str]] = None

    while retry_count < max_network_retries:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(rroot),
                capture_output=True,
                text=True,
                timeout=build_timeout,
                env=os.environ.copy(),
            )
            output = (result.stdout or "") + (result.stderr or "")

            is_network_error = (
                "network" in output.lower()
                or "timeout" in output.lower()
                or "could not connect" in output.lower()
                or (
                    "failed to solve" in output.lower()
                    and "docker.io" in output.lower()
                )
            )

            if (
                result.returncode != 0
                and is_network_error
                and retry_count < max_network_retries - 1
            ):
                retry_count += 1
                wait_time = 2**retry_count
                _v(
                    paint(
                        "33",
                        f"Network-like error; retry in {wait_time}s ({retry_count}/{max_network_retries})...",
                    )
                )
                time.sleep(wait_time)
                continue

            break

        except subprocess.TimeoutExpired:
            if retry_count < max_network_retries - 1:
                retry_count += 1
                wait_time = 2**retry_count
                _v(
                    paint(
                        "33",
                        f"Build timed out; retry in {wait_time}s ({retry_count}/{max_network_retries})...",
                    )
                )
                time.sleep(wait_time)
                continue
            msg = f"Docker build timed out after {build_timeout}s (retries exhausted)"
            _v(paint("31", msg))
            if verbose:
                print(paint("1;36", "==============================================\n"), file=sys.stderr)
            return False, msg
        except OSError as e:
            msg = f"Error running docker build: {e}"
            _v(paint("31", msg))
            if verbose:
                print(paint("1;36", "==============================================\n"), file=sys.stderr)
            return False, msg

    if result is None:
        msg = "Docker build failed (no result after retries)"
        _v(paint("31", msg))
        if verbose:
            print(paint("1;36", "==============================================\n"), file=sys.stderr)
        return False, msg

    output = (result.stdout or "") + (result.stderr or "")

    if result.returncode != 0 and (
        "permission denied" in output.lower() or "dial unix" in output.lower()
    ):
        extra = (
            "\n\nNOTE: Docker socket permission issue (not necessarily a Dockerfile bug).\n"
            "Try: sudo usermod -aG docker $USER && newgrp docker\n"
        )
        full = output + extra
        _v(paint("31", full[:4000] + ("..." if len(full) > 4000 else "")))
        if verbose:
            print(paint("1;36", "==============================================\n"), file=sys.stderr)
        return False, full

    if result.returncode == 0:
        _v(paint("32", "✓ Docker build succeeded"))
        if verbose and output.strip():
            print(paint("90", "--- build output (tail) ---"), file=sys.stderr)
            tail = output.strip()[-8000:] if len(output) > 8000 else output.strip()
            print(paint("32", tail), file=sys.stderr)
        if verbose:
            print(paint("1;36", "==============================================\n"), file=sys.stderr)
        return True, output

    _v(paint("31", "✗ Docker build failed"))
    if verbose:
        print(paint("90", "--- full build log ---"), file=sys.stderr)
        print(paint("31", output), file=sys.stderr)
        print(paint("1;36", "==============================================\n"), file=sys.stderr)
    return False, output


__all__ = ["check_docker_permission", "dockerbuild"]
