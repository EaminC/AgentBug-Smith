#!/usr/bin/env python3
"""
Scans key repository files, loads prompts from prompt/dockerbuild/init, config from
conf/dockerbuild/init, and calls the LLM to write a Dockerfile.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from forge.api import LLMClient  # noqa: E402


def _color_on() -> bool:
    return sys.stdout.isatty() and not (os.getenv("NO_COLOR") or "").strip()


def _paint(code: str, text: str) -> str:
    if not _color_on():
        return text
    return f"\033[{code}m{text}\033[0m"


def _log_verbose(tag: str, message: str, *, color: str = "33") -> None:
    """Yellow tag, default message color."""
    print(f"{_paint(color, tag)} {message}")


@dataclass(frozen=True)
class DockerbuildInitPaths:
    """Resolved paths under repo root for conf/ and prompt/."""

    repo_root: Path
    conf_dir: Path
    prompt_dir: Path


def default_dockerbuild_init_paths() -> DockerbuildInitPaths:
    """Paths to ``conf/dockerbuild/init`` and ``prompt/dockerbuild/init`` under this repo."""
    root = PROJECT_ROOT.resolve()
    return DockerbuildInitPaths(
        repo_root=root,
        conf_dir=root / "conf" / "dockerbuild" / "init",
        prompt_dir=root / "prompt" / "dockerbuild" / "init",
    )


def load_scan_config(paths: DockerbuildInitPaths) -> Dict[str, Any]:
    path = paths.conf_dir / "scan.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_prompt_bundle(paths: DockerbuildInitPaths) -> Dict[str, str]:
    d = paths.prompt_dir
    return {
        "system": _read_text(d / "system.txt"),
        "user_prefix": _read_text(d / "user_prefix.txt"),
        "user_suffix": _read_text(d / "user_suffix.txt"),
    }


def find_target_files(repo_root: Path, scan: Dict[str, Any]) -> List[Path]:
    target_files: List[str] = scan["target_files"]
    target_globs: List[str] = scan["target_globs"]
    found: List[Path] = []

    for name in target_files:
        path = repo_root / name
        if path.exists():
            found.append(path)

    for pattern in target_globs:
        found.extend(repo_root.glob(pattern))

    unique: List[Path] = []
    seen = set()
    for p in found:
        if p.exists():
            key = p.resolve()
            if key not in seen:
                seen.add(key)
                unique.append(p)
    return unique


def read_files(repo_root: Path, files: List[Path]) -> List[Dict[str, str]]:
    results = []
    root = repo_root.resolve()
    for file in files:
        try:
            relative_path = file.resolve().relative_to(root)
        except ValueError:
            relative_path = Path(file).name
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            results.append({"path": str(relative_path).replace("\\", "/"), "content": content})
        except Exception as e:  # pragma: no cover
            results.append(
                {"path": str(relative_path).replace("\\", "/"), "content": f"<<READ ERROR: {e}>>"}
            )
    return results


def _known_test_paths_block(test_paths_list: Optional[List[str]]) -> str:
    if not test_paths_list:
        return ""
    joined = ", ".join(p.strip() for p in test_paths_list if p and isinstance(p, str))
    if not joined:
        return ""
    return (
        "   **Known test paths for this repo** (ensure Dockerfile supports running them): "
        f"{joined}\n"
    )


def build_prompt(
    prompts: Dict[str, str],
    file_entries: List[Dict[str, str]],
    test_paths_list: Optional[List[str]] = None,
) -> str:
    block = _known_test_paths_block(test_paths_list)
    prefix = prompts["user_prefix"].replace("{{KNOWN_TEST_PATHS_BLOCK}}", block)

    parts: List[str] = [prefix]

    for item in file_entries:
        path_str = item["path"].replace("\\", "/")
        parts.append(f"### {path_str}")
        parts.append(item["content"])
        parts.append("")

    parts.append(prompts["user_suffix"].rstrip())
    return "\n".join(parts)


def _preview(text: str, max_chars: int = 600) -> str:
    t = text.replace("\r\n", "\n")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + f"\n... ({len(t)} chars total, truncated)"


def ask_ai(
    system: str,
    user_prompt: str,
    model: Optional[str] = None,
    *,
    verbose: bool = False,
) -> str:
    client = LLMClient(model=model)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_prompt},
    ]
    if verbose:
        src = (
            "explicit `model` overrides root `.env` MODEL"
            if model
            else "using MODEL from `.env` (or LLMClient default)"
        )
        print(_paint("1;36", "\n========== LLM exchange =========="))
        _log_verbose("[model]", _paint("32", client.model), color="1;33")
        print(f"{_paint('90', '[model source]')} {src}")
        print(f"{_paint('35', '[system]')} ({len(system)} chars)\n{_preview(system, 800)}")
        print(
            f"{_paint('35', '[user]')} ({len(user_prompt)} chars, includes repo files)\n"
            f"{_preview(user_prompt, 1200)}"
        )
        print(_paint("34", "---------- calling API ----------"))
    result = client.chat(messages=messages)
    if verbose:
        print(_paint("34", "---------- assistant reply ----------"))
        out = result or ""
        body = _preview(out, 8000) if len(out) > 8000 else (out or "(empty)")
        print(_paint("32", body) if out else _paint("90", body))
        print(_paint("1;36", "==================================\n"))
    return result


def generate_dockerfile_from_repo(
    repo_root: Path | str,
    dockerfile_out: Path | str,
    *,
    test_paths: Optional[List[str]] = None,
    model: Optional[str] = None,
    init_paths: Optional[DockerbuildInitPaths] = None,
    verbose: bool = False,
) -> Path:
    """
    Scan a local repo, call the LLM, and write the Dockerfile to ``dockerfile_out``.

    Configuration and prompt text are loaded from ``conf/dockerbuild/init`` and
    ``prompt/dockerbuild/init`` relative to the AgentSmith-Live repo root (the parent
    of ``src/``), unless ``init_paths`` is provided.

    If ``model`` is passed, it overrides ``MODEL`` in the root ``.env`` (same as
    :class:`forge.api.LLMClient`). With ``verbose=True``, prints a scan summary and
    the LLM request/response (long text is truncated in previews).
    """
    repo = Path(repo_root).resolve()
    out = Path(dockerfile_out).resolve()
    paths = init_paths or default_dockerbuild_init_paths()

    if verbose:
        _log_verbose("[dockerinit]", f"repo: {_paint('32', str(repo))}", color="1;33")
        _log_verbose("[dockerinit]", f"output: {_paint('32', str(out))}", color="1;33")

    scan = load_scan_config(paths)
    prompts = load_prompt_bundle(paths)

    files = find_target_files(repo, scan)
    if verbose:
        _log_verbose("[dockerinit]", f"context files: {_paint('36', str(len(files)))}", color="1;33")
    file_entries = read_files(repo, files)

    resolved_test_paths: List[str] = list(test_paths) if test_paths else []
    if not resolved_test_paths:
        try:
            raw = os.environ.get("REPO_TEST_PATHS")
            if raw:
                resolved_test_paths = json.loads(raw)
        except Exception:
            pass

    for p in resolved_test_paths:
        if not isinstance(p, str) or not p.strip():
            continue
        norm = p.strip().replace("\\", "/")
        full = repo / norm
        if full.is_file() and full.exists():
            if not any(e.get("path") == norm for e in file_entries):
                try:
                    content = full.read_text(encoding="utf-8", errors="replace")
                    file_entries.append({"path": norm, "content": content})
                except Exception:
                    pass

    prompt = build_prompt(prompts, file_entries, test_paths_list=resolved_test_paths or None)
    if verbose:
        _log_verbose(
            "[dockerinit]",
            f"merged user prompt length: {_paint('36', str(len(prompt)))} chars",
            color="1;33",
        )
    ai_result = ask_ai(prompts["system"], prompt, model=model, verbose=verbose)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ai_result, encoding="utf-8")
    return out


# Short alias for one-liners (same as :func:`generate_dockerfile_from_repo`).
dockerinit = generate_dockerfile_from_repo
# Next: :func:`dockerbuild.write.dockerwrite` then :func:`dockerbuild.build.dockerbuild`.


def run_docker_build_flow(
    repo_root: Path,
    test_paths: Optional[List[str]] = None,
    dockerfile_out: Optional[Path] = None,
) -> Path:
    """Backward-compatible wrapper: writes to ``dockerfile_out`` or ``repo_root/env.dockerfile``."""
    out = dockerfile_out or (repo_root / "env.dockerfile")
    return generate_dockerfile_from_repo(repo_root, out, test_paths=test_paths)


def main() -> None:
    repo_root = Path.cwd()
    try:
        result_path = run_docker_build_flow(repo_root)
        print("\n--- SUCCESS ---")
        print(f"env.dockerfile successfully generated at: {result_path}")
    except Exception as e:
        print("\n--- ERROR ---", file=sys.stderr)
        print(f"An error occurred during the process: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
