"""
Standalone Docker test utilities for quick local checks.

This module intentionally does not touch the end-to-end pipeline in ``exp/end-end.py``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from dockerbuild.build import dockerbuild  # noqa: E402
from forge.api import LLMClient  # noqa: E402
from utils.lang_detect import detect_project_language  # noqa: E402

_PROMPT_DIR = PROJECT_ROOT / "prompt" / "testrun"
_GET_TEST_PATH_USER_PROMPT = _PROMPT_DIR / "get_test_file_path_user.txt"
_LANGCHAIN_TEST_DOCKERFILE_TEMPLATE = _PROMPT_DIR / "langchain_test_runner.Dockerfile"


def _strip_code_fence(text: str) -> str:
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _list_candidate_test_files(repo_root: Path) -> List[str]:
    ignored = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "target",
    }
    out: List[str] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in ignored for part in p.parts):
            continue
        rel = p.relative_to(repo_root).as_posix()
        name = p.name.lower()
        parent = p.parent.name.lower()
        rel_low = rel.lower()
        if rel_low.startswith(".github/") or name == "__init__.py":
            # CI helper scripts and package marker files are poor first-test choices.
            continue
        if (
            "/test" in rel_low
            or "/tests" in rel_low
            or parent in {"test", "tests", "__tests__"}
            or name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.js")
            or name.endswith(".spec.ts")
            or name.endswith("_test.go")
            or name.endswith("_test.rs")
        ):
            out.append(rel)
    out.sort()
    return out


def _normalize_repo_rel_path(p: str) -> str:
    s = p.strip().replace("\\", "/")
    if s.startswith("./"):
        s = s[2:]
    return s


def _json_paths_from_llm(raw: str) -> List[str]:
    body = _strip_code_fence(raw)
    if not body:
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        arr = data.get("test_paths", [])
    elif isinstance(data, list):
        arr = data
    else:
        arr = []
    if not isinstance(arr, list):
        return []
    paths: List[str] = []
    for x in arr:
        if not isinstance(x, str):
            continue
        s = _normalize_repo_rel_path(x)
        if s:
            paths.append(s)
    return paths


def _build_get_test_file_prompt(candidates: List[str], max_items: int) -> str:
    candidates_text = "\n".join(candidates[:500])
    if _GET_TEST_PATH_USER_PROMPT.is_file():
        template = _GET_TEST_PATH_USER_PROMPT.read_text(encoding="utf-8")
        return template.format(max_items=max_items, candidates=candidates_text)
    return (
        "You are selecting runnable existing test files from a repository.\n"
        "Return strict JSON only with this schema:\n"
        '{"test_paths": ["relative/path/to/test.ext"]}\n'
        "Rules:\n"
        "- Paths must already exist in the candidate list.\n"
        "- Prefer directly runnable unit/integration tests.\n"
        f"- Return up to {max_items} items.\n\n"
        "Candidate paths:\n"
        + candidates_text
    )


def get_test_file_path(
    repo_path: Path | str,
    *,
    model: Optional[str] = None,
    max_items: int = 20,
    verbose: bool = False,
) -> List[str]:
    """
    Ask Forge for a JSON list of existing test paths in ``repo_path``.

    Returns a de-duplicated list of repo-relative paths. If Forge output is empty/invalid,
    falls back to local rule-based file discovery.
    """
    repo_root = Path(repo_path).resolve()
    candidates = _list_candidate_test_files(repo_root)
    if not candidates:
        return []

    prompt = _build_get_test_file_prompt(candidates, max_items)
    system = "Output JSON only. No markdown."
    client = LLMClient(model=model)
    raw = client.simple_chat(prompt, system_prompt=system, temperature=0.0)
    picked = _json_paths_from_llm(raw)

    existing = {p.as_posix() for p in repo_root.rglob("*") if p.is_file()}
    valid: List[str] = []
    seen = set()
    for rel in picked:
        rel = _normalize_repo_rel_path(rel)
        if rel in existing and rel not in seen:
            valid.append(rel)
            seen.add(rel)
        if len(valid) >= max_items:
            break

    if valid:
        return valid

    fallback = candidates[:max_items]
    if verbose:
        print("[docker_test_tool] Forge returned empty/invalid JSON. Using fallback candidates.", file=sys.stderr)
    return fallback


def _last_workdir_in_dockerfile(dockerfile: Path) -> Optional[str]:
    if not dockerfile.is_file():
        return None
    last: Optional[str] = None
    for raw in dockerfile.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("WORKDIR "):
            rest = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else ""
            val = rest.strip().strip('"').strip("'")
            if val:
                last = val
    return last


def _default_run_argv(repo_root: Path, test_rel: str) -> List[str]:
    lang = detect_project_language(repo_root)
    name = lang.get("name", "Python")
    if name == "Python":
        # LangChain monorepo: each subpackage manages test deps via uv/pyproject.
        pkg_prefixes = [
            "libs/core/",
            "libs/langchain/",
            "libs/langchain_v1/",
            "libs/text-splitters/",
            "libs/standard-tests/",
        ]
        for pref in pkg_prefixes:
            if test_rel.startswith(pref):
                pkg_dir = pref[:-1]
                local_test_path = test_rel[len(pref) :]
                return ["uv", "run", "--directory", pkg_dir, "pytest", "-q", local_test_path]
        return ["python", "-m", "pytest", "-q", test_rel]
    if name in {"JavaScript", "TypeScript"}:
        return ["npm", "test", "--", test_rel]
    if name == "Go":
        return ["go", "test", test_rel]
    if name == "Rust":
        stem = Path(test_rel).stem
        return ["cargo", "test", "--test", stem]
    if name == "Java":
        cls = Path(test_rel).stem
        return ["mvn", "test", f"-Dtest={cls}"]
    return ["python", "-m", "pytest", "-q", test_rel]


def ensure_langchain_test_dockerfile(
    repo_path: Path | str,
    *,
    relpath: str = "libs/langchain/test_runner.Dockerfile",
    overwrite: bool = True,
) -> Path:
    """
    Ensure a test-focused Dockerfile exists in the langchain repo.

    The file is created from ``prompt/testrun/langchain_test_runner.Dockerfile`` when missing.
    Returns the repo-relative path.
    """
    repo_root = Path(repo_path).resolve()
    out = repo_root / relpath
    if out.is_file() and not overwrite:
        return Path(relpath)
    if not _LANGCHAIN_TEST_DOCKERFILE_TEMPLATE.is_file():
        raise FileNotFoundError(
            f"Missing Dockerfile template: {_LANGCHAIN_TEST_DOCKERFILE_TEMPLATE}"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    body = _LANGCHAIN_TEST_DOCKERFILE_TEMPLATE.read_text(encoding="utf-8")
    out.write_text(body, encoding="utf-8")
    return Path(relpath)


def docker_test_repo_test(
    repo_path: Path | str,
    dockerfile_path: Path | str,
    test_file_path: Path | str,
    *,
    run_argv: Optional[List[str]] = None,
    platform: str = "linux/amd64",
    timeout: int = 600,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    Build docker image with ``dockerfile_path``, then run one test file in container.

    Returns ``(passed, report)``.
    """
    repo_root = Path(repo_path).resolve()
    dockerfile = Path(dockerfile_path)
    if dockerfile.is_absolute():
        dockerfile_rel = dockerfile.relative_to(repo_root).as_posix()
    else:
        dockerfile_rel = dockerfile.as_posix()

    test_path = Path(test_file_path)
    if test_path.is_absolute():
        test_rel = test_path.relative_to(repo_root).as_posix()
    else:
        test_rel = _normalize_repo_rel_path(test_path.as_posix())

    ok, build_log = dockerbuild(
        repo_root,
        dockerfile=dockerfile_rel,
        project_root=PROJECT_ROOT,
        verbose=verbose,
        platform=platform,
    )
    if not ok:
        return False, "Docker build failed:\n" + build_log[-12000:]

    image_tag = f"test-build-{repo_root.name.lower()}"
    argv = run_argv or _default_run_argv(repo_root, test_rel)
    workdir = _last_workdir_in_dockerfile(repo_root / dockerfile_rel)

    cmd: List[str] = ["docker", "run", "--rm", "--platform", platform]
    if workdir:
        cmd.extend(["-w", workdir])
    cmd.append(image_tag)
    cmd.extend(argv)

    try:
        r = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"docker run timeout after {timeout}s"
    except OSError as e:
        return False, f"docker run failed: {e}"

    out = (r.stdout or "") + (r.stderr or "")
    report = (
        f"dockerfile={dockerfile_rel}\n"
        f"test={test_rel}\n"
        f"cmd={' '.join(cmd)}\n"
        f"exit_code={r.returncode}\n\n"
        f"{out[-12000:]}"
    )
    return r.returncode == 0, report


__all__ = ["get_test_file_path", "docker_test_repo_test", "ensure_langchain_test_dockerfile"]
