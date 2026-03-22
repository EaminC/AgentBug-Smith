"""
Generate a single fail2pass-style test file from an issue JSON via the Forge LLM.

Loads prompts from ``prompt/testgen`` under the AgentSmith project root. The user message includes
issue body, ``existing_test_paths``, full contents of ``test_paths_in_patch`` when present, and the
fix patch — so the model can align with downstream Docker/pytest workflows.

This module only **writes** the generated file; it does not run pytest, Docker, or ``git apply``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from forge.api import LLMClient  # noqa: E402
from repo.term import log_line, paint  # noqa: E402


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    while lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


@dataclass(frozen=True)
class IssueTestgenContext:
    issue_json_path: Path
    issue_number: int
    title: str
    body: str
    patch: str
    base_sha: Optional[str]
    test_paths_in_patch: List[str]
    existing_test_paths: List[str]


def load_issue_testgen_context(issue_json_path: Path | str) -> IssueTestgenContext:
    path = Path(issue_json_path).resolve()
    with open(path, encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    num = int(data.get("number") or 0)
    title = str(data.get("title") or "")
    body = str(data.get("body") or "")

    patch = ""
    base_sha: Optional[str] = None
    in_patch: List[str] = []
    prs = [p for p in (data.get("linked_prs") or []) if isinstance(p, dict)]

    for pr in prs:
        p = pr.get("patch")
        if isinstance(p, str) and p.strip():
            patch = p.strip()
            bs = pr.get("base_sha")
            if isinstance(bs, str) and bs.strip():
                base_sha = bs.strip()
            raw = pr.get("test_paths_in_patch") or []
            if isinstance(raw, list):
                in_patch = [
                    str(x).strip().replace("\\", "/")
                    for x in raw
                    if isinstance(x, str) and str(x).strip()
                ]
            break

    if not in_patch:
        for pr in prs:
            raw = pr.get("test_paths_in_patch") or []
            if isinstance(raw, list):
                in_patch = [
                    str(x).strip().replace("\\", "/")
                    for x in raw
                    if isinstance(x, str) and str(x).strip()
                ]
            if in_patch:
                break

    existing = data.get("existing_test_paths") or []
    if not isinstance(existing, list):
        existing = []
    existing_paths = [str(x).strip().replace("\\", "/") for x in existing if isinstance(x, str) and str(x).strip()]

    return IssueTestgenContext(
        issue_json_path=path,
        issue_number=num,
        title=title,
        body=body,
        patch=patch,
        base_sha=base_sha,
        test_paths_in_patch=in_patch,
        existing_test_paths=existing_paths,
    )


def read_repo_text(
    repo_root: Path,
    rel: str,
    *,
    max_chars: Optional[int] = None,
) -> Optional[str]:
    """
    Read a file under ``repo_root``. By default **no** length cap (full file for prompt context).
    Pass ``max_chars`` only if you need an explicit limit.
    """
    p = (repo_root / rel).resolve()
    try:
        root = repo_root.resolve()
        p.relative_to(root)
    except ValueError:
        return None
    if not p.is_file():
        return None
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if max_chars is not None and len(t) > max_chars:
        return t[:max_chars] + f"\n... ({len(t)} chars total, truncated)"
    return t


def _default_prompt_paths(project_root: Path) -> Path:
    return project_root.resolve() / "prompt" / "testgen"


def build_testgen_user_prompt(
    ctx: IssueTestgenContext,
    repo_root: Path,
    out_rel: str,
    feedback: Optional[str] = None,
) -> str:
    parts: List[str] = []
    parts.append("--- TASK: WRITE ONE FAIL2PASS TEST FILE ---\n")
    parts.append(
        "Context: the repo is already checked out locally (e.g. after an end-to-end clone). A typical "
        "pipeline **will** use it like this — design your test so these steps make sense:\n"
        "  1) **Buggy tree:** build/run from the repo root (e.g. `docker build` using `env.dockerfile` if present), "
        "then run **your** test inside the environment (e.g. `pytest` on this file). The **test process** should "
        "exit with **non-zero** (failure).\n"
        "  2) Apply the unified diff under `linked_prs[].patch` (e.g. `git apply`) so the working tree matches the **fixed** code.\n"
        "  3) **Fixed tree:** rebuild if needed, run the **same** test command again. The **test process** should "
        "exit with **0** (success).\n"
        "Pass/fail is defined by the **pytest (or project test runner) exit code**, not by any outer driver script.\n"
    )
    parts.append(
        "If you can run commands in your environment, you **may** run `pytest` or Docker yourself to validate "
        "before you answer; the deliverable is still a single Python file.\n"
    )
    parts.append(f"\n--- OUTPUT FILE (must match this path) ---\n{out_rel}\n")

    parts.append("\n--- ISSUE (description of the bug) ---\n")
    parts.append(f"number: {ctx.issue_number}\n")
    parts.append(f"title: {ctx.title}\n")
    parts.append("body (full text, not truncated):\n")
    parts.append(ctx.body)

    if ctx.test_paths_in_patch:
        parts.append(
            "\n\n"
            "================================================================================\n"
            "CRITICAL — IN-PATCH TEST FILES (same bug; patch touches these tests)\n"
            "================================================================================\n"
            "The issue JSON lists `test_paths_in_patch`: these paths are **directly tied to this bug** "
            "and appear in the fix patch as test-related changes. **Do not** only use the path string — "
            "the **full current file contents** from the checked-out repo are below. Read them end-to-end; "
            "your new test should be consistent with the project’s testing style here and assert behavior "
            "that flips from failing before the patch to passing after.\n"
        )
        for rel in ctx.test_paths_in_patch:
            content = read_repo_text(repo_root, rel)
            parts.append(f"\n### Path: `{rel}`\n")
            if content is None:
                parts.append("<< FILE NOT FOUND IN REPO AT THIS PATH >>\n")
            else:
                parts.append(content)
    else:
        parts.append(
            "\n\n--- IN-PATCH TEST PATHS ---\n"
            "`test_paths_in_patch` is empty in the issue JSON; infer from the issue body, patch, and "
            "existing tests below.\n"
        )

    parts.append(
        "\n\n"
        "--- EXISTING TEST PATHS IN REPO (reference only; file paths for style / discovery) ---\n"
        "These are paths under the repository that may help you match naming, layout, and fixtures. "
        "You are **not** required to open every file; use them as hints.\n"
    )
    for p in ctx.existing_test_paths:
        parts.append(p)

    parts.append(
        "\n\n--- FIX PATCH (`linked_prs[].patch`): unified diff (what the fixed tree changes) ---\n"
    )
    parts.append(ctx.patch if ctx.patch else "<< NO PATCH IN ISSUE JSON >>\n")
    if ctx.base_sha:
        parts.append(f"\n(PR base commit recorded in JSON: `{ctx.base_sha}` — patch applies to that tree.)\n")

    parts.append(
        "\n\n--- REMINDER ---\n"
        "Respond with the **complete** Python test file only (path above). Match imports and conventions of this repo.\n"
    )
    if feedback and feedback.strip():
        parts.append(
            "\n\n--- PREVIOUS FAIL2PASS VERIFY (adjust your test) ---\n"
            "The pipeline ran Docker + pytest + ``git apply`` + pytest again. Use this to fix the test.\n"
        )
        parts.append(feedback.strip())
    return "\n".join(parts)


def ask_testgen_llm(
    system: str,
    user: str,
    model: Optional[str] = None,
    *,
    verbose: bool = False,
) -> str:
    client = LLMClient(model=model)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if verbose:
        src = (
            "explicit `model=` overrides root `.env` MODEL"
            if model
            else "using MODEL from `.env` (or LLMClient default)"
        )
        print(paint("1;36", "\n========== LLM exchange (testgen) =========="), file=sys.stderr)
        log_line("[testgen]", paint("1;33", "[model]"), paint("32", client.model))
        print(f"{paint('90', '[model source]')} {src}", file=sys.stderr)
        print(f"{paint('35', '[system]')} ({len(system)} chars, full below)\n{system}", file=sys.stderr)
        print(f"{paint('35', '[user]')} ({len(user)} chars, full below)\n{user}", file=sys.stderr)
        print(paint("34", "---------- calling API ----------"), file=sys.stderr)
    out = client.chat(messages=messages, temperature=0.3)
    text = (out or "").strip()
    if verbose:
        print(paint("34", "---------- assistant reply ----------"), file=sys.stderr)
        body = text or "(empty)"
        print(paint("32", body) if text else paint("90", body), file=sys.stderr)
        print(paint("1;36", "==================================\n"), file=sys.stderr)
    return text


def testgen(
    repo_root: Path | str,
    issue_json_path: Path | str,
    *,
    project_root: Optional[Path] = None,
    model: Optional[str] = None,
    verbose: bool = False,
    out_test_relpath: Optional[str] = None,
    feedback: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Call the LLM with issue context (body, ``existing_test_paths``, in-patch file contents, patch)
    and write **one** Python test file under ``repo_root``.

    Does not run Docker, pytest, or ``git apply`` here; the prompt explains the intended fail2pass
    pipeline for the model. Returns ``(True, summary)`` on success.
    """
    root = Path(project_root or PROJECT_ROOT).resolve()
    rroot = Path(repo_root).resolve()
    ctx = load_issue_testgen_context(issue_json_path)

    n = ctx.issue_number or 0
    rel = out_test_relpath or f"tests/agentsmith_fail2pass_{n or 'issue'}.py"
    rel = rel.strip().replace("\\", "/")

    system_path = _default_prompt_paths(root) / "system.txt"
    system = (
        system_path.read_text(encoding="utf-8")
        if system_path.is_file()
        else "You output only a valid Python test file, no markdown."
    )
    user = build_testgen_user_prompt(ctx, rroot, rel, feedback=feedback)

    if verbose:
        log_line("[testgen]", paint("90", "repo:"), paint("32", str(rroot)))
        log_line("[testgen]", paint("90", "issue json:"), paint("32", str(ctx.issue_json_path)))
        log_line("[testgen]", paint("90", "out test file:"), paint("36", rel))

    raw = ask_testgen_llm(system, user, model=model, verbose=verbose)
    code_body = _strip_code_fence(raw)
    if not code_body.strip():
        return False, "LLM returned empty test file content."

    out_path = rroot / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(code_body + ("\n" if not code_body.endswith("\n") else ""), encoding="utf-8")

    msg = f"Wrote test file: {out_path}"
    return True, msg


__all__ = [
    "IssueTestgenContext",
    "build_testgen_user_prompt",
    "load_issue_testgen_context",
    "testgen",
]
