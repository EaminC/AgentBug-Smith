"""
``dockerwrite``: after ``dockerinit`` produces ``env.dockerfile``, run the ``claude -p ...``
CLI so the model **overwrites** ``env.dockerfile`` in the target repo.

Config: ``conf/dockerbuild/write``, prompts: ``prompt/dockerbuild/write``.
Unlike SWEGENT-BENCH ``repo-build``, this omits mock/API example sections (no mock_interface).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
import re
from typing import Dict, List, Optional

from dotenv import dotenv_values, load_dotenv

_DOCKER_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from repo.term import log_line, paint


def _getenv_stripped(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    if v is None:
        return default
    return str(v).strip().strip('"').strip("'")


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"[File not found: {path}]"
    except OSError as e:
        return f"[Error reading {path}: {e}]"


def _conf_dir(project_root: Path) -> Path:
    return project_root / "conf" / "dockerbuild" / "write"


def _prompt_dir(project_root: Path) -> Path:
    return project_root / "prompt" / "dockerbuild" / "write"


def _load_existing_dockerfile(repo_root: Path) -> Optional[str]:
    """Load ``env.dockerfile`` at repo root (from dockerinit), if present."""
    p = repo_root / "env.dockerfile"
    if p.is_file():
        return _load_text(p)
    return None


def _normalize_to_env_dockerfile(repo_root: Path) -> None:
    """
    If the model still wrote ``claude.dockerfile``, copy its contents onto ``env.dockerfile``
    (overwrite) and remove ``claude.dockerfile``.
    """
    rroot = repo_root.resolve()
    legacy = rroot / "claude.dockerfile"
    target = rroot / "env.dockerfile"
    if not legacy.is_file():
        return
    text = legacy.read_text(encoding="utf-8", errors="replace")
    target.write_text(text, encoding="utf-8")
    legacy.unlink(missing_ok=True)


def _preview(text: str, max_chars: int = 600) -> str:
    """Truncate long prompt text for stderr preview (same idea as ``dockerinit``)."""
    t = text.replace("\r\n", "\n")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + f"\n... ({len(t)} chars total, truncated)"


def _docker_env_quote(value: str) -> str:
    """Double-quote a value for use in a Dockerfile ``ENV`` line."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _read_dotenv_mapping(project_root: Path) -> Dict[str, str]:
    """
    Parse ``project_root/.env`` into a name→value map (does not rely on ``os.environ``).
    Uses ``python-dotenv`` so quoting and ``export`` lines match ``load_dotenv`` behavior.
    """
    path = project_root.resolve() / ".env"
    if not path.is_file():
        return {}
    raw = dotenv_values(path)
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if k is None or not str(k).strip():
            continue
        ks = str(k).strip()
        out[ks] = "" if v is None else str(v)
    return out


def _inject_project_dotenv_into_env_dockerfile(
    repo_root: Path, project_root: Path, *, verbose: bool = False
) -> None:
    """
    After Claude writes ``env.dockerfile``:

    1. Read **all** variables from ``project_root/.env``.
    2. Replace ``${VAR}`` with literal values (longest keys first to avoid partial matches).
    3. If the inject marker is missing, insert one ``ENV`` line per valid name after the first ``FROM``.
    """
    mapping = _read_dotenv_mapping(project_root)
    path = repo_root / "env.dockerfile"
    if not path.is_file():
        return

    if not mapping:
        if verbose:
            log_line(
                "[dockerwrite]",
                paint("33", ".env inject skipped:"),
                paint("90", f"no variables in {project_root.resolve() / '.env'}"),
            )
        return

    text = path.read_text(encoding="utf-8", errors="replace")

    for name in sorted(mapping.keys(), key=len, reverse=True):
        text = text.replace("${" + name + "}", mapping[name])

    marker = "AgentSmith inject .env"
    if marker not in text:
        lines_out: List[str] = [
            f"\n# --- {marker} from project root (dockerwrite) ---\n",
        ]
        for name in mapping:
            if not _DOCKER_ENV_NAME.match(name):
                if verbose:
                    log_line(
                        "[dockerwrite]",
                        paint("33", "skip ENV (invalid name):"),
                        paint("90", name),
                    )
                continue
            lines_out.append(f"ENV {name}={_docker_env_quote(mapping[name])}\n")
        lines_out.append("# --- end inject ---\n")
        block = "".join(lines_out)
        lines = text.splitlines(keepends=True)
        out: List[str] = []
        inserted = False
        for line in lines:
            out.append(line)
            if not inserted and line.strip().upper().startswith("FROM "):
                out.append(block)
                inserted = True
        text = "".join(out) if inserted else block + text

    path.write_text(text, encoding="utf-8")


def _env_pool_merged_with_root_dotenv(project_root: Path, env_pool_raw: str) -> str:
    """
    Merge **all** key/value pairs from project root ``.env`` into the env_pool JSON text
    (same keys as on disk; avoids placeholders in the prompt).
    """
    _load_root_dotenv(project_root)
    try:
        data = json.loads(env_pool_raw)
    except json.JSONDecodeError:
        return env_pool_raw
    for k, v in _read_dotenv_mapping(project_root).items():
        data[k] = v
    return json.dumps(data, indent=2)


def build_dockerwrite_prompt(
    project_root: Path,
    repo_root: Path,
    feedback: Optional[str] = None,
) -> str:
    """
    Assemble the full prompt for ``claude`` (mock / API example sections omitted).
    Loads project root ``.env`` so Forge values embedded in the prompt match ``FORGE_*`` on disk.
    """
    root = project_root.resolve()
    rroot = repo_root.resolve()
    pdir = _prompt_dir(root)
    cdir = _conf_dir(root)

    _load_root_dotenv(root)

    repo_structure = None
    raw_rs = os.getenv("REPO_STRUCTURE")
    if raw_rs:
        try:
            repo_structure = json.loads(raw_rs)
        except json.JSONDecodeError:
            pass

    instructions = _load_text(pdir / "instructions.txt").strip()
    task = _load_text(pdir / "task.txt").strip()
    model_list = _load_text(cdir / "model-list.json")
    env_pool_raw = _load_text(cdir / "env_pool.json")
    env_pool = _env_pool_merged_with_root_dotenv(root, env_pool_raw)

    parts: List[str] = []
    parts.append("=" * 80)
    parts.append("IMPORTANT INSTRUCTIONS")
    parts.append("=" * 80)
    parts.append(instructions)
    parts.append("")

    parts.append("=" * 80)
    parts.append("OVERWRITE RULE FOR env.dockerfile (READ CAREFULLY)")
    parts.append("=" * 80)
    parts.append(
        "When you save **env.dockerfile**, you must **replace the entire file** with your final Dockerfile text."
    )
    parts.append(
        "**Forbidden:** appending new instructions after the old content, or duplicating the previous Dockerfile and adding blocks at the bottom."
    )
    parts.append(
        "**Required:** one complete Dockerfile; if multi-stage, design it as a whole. The editor save must be a full overwrite, not a patch or append."
    )
    parts.append("")

    parts.append("=" * 80)
    parts.append("AVAILABLE MODELS")
    parts.append("=" * 80)
    parts.append("These models are available through Forge API:")
    parts.append(model_list)
    parts.append("")

    parts.append("=" * 80)
    parts.append("ENVIRONMENT VARIABLES REFERENCE (merged from project root .env)")
    parts.append("=" * 80)
    parts.append(
        "Values below include **FORGE_API_KEY** / **FORGE_BASE_URL** read from the AgentSmith "
        "project root `.env` when this prompt was built. Use them in `ENV` lines — do **not** use "
        "placeholders such as `your-forge-api-key-here`."
    )
    if not _getenv_stripped("FORGE_API_KEY"):
        parts.append(
            "WARNING: `FORGE_API_KEY` was empty or missing in project root `.env` — the JSON may still "
            "show a placeholder; set the key in `.env` and re-run, or use `ARG FORGE_API_KEY` with build-time passing."
        )
    parts.append("Set these in the Dockerfile (ENV and/or ARG as appropriate):")
    parts.append(env_pool)
    parts.append("")

    existing_content = _load_existing_dockerfile(rroot)
    if existing_content and not existing_content.startswith("["):
        parts.append("=" * 80)
        parts.append("EXISTING env.dockerfile (from dockerinit — full replace, not append)")
        parts.append("=" * 80)
        if feedback:
            parts.append("This is the current env.dockerfile that failed to build:")
        else:
            parts.append(
                "dockerinit wrote env.dockerfile at the repo root. You must **overwrite** that file: "
                "write a **complete new Dockerfile** as the full file contents. **Do not append** to what is below."
            )
        parts.append("")
        parts.append(existing_content)
        parts.append("")
        if not feedback:
            parts.append(
                "TASK: Save your result by **replacing** env.dockerfile entirely (same path). "
                "Do not concatenate or append to the text above."
            )
            parts.append("If the Dockerfile is already acceptable, you may output an equivalent full file.")

    parts.append("")

    if feedback:
        parts.append("=" * 80)
        parts.append("PREVIOUS BUILD FEEDBACK")
        parts.append("=" * 80)
        parts.append("The previous Docker build attempt failed. Here is the error information:")
        parts.append("")
        parts.append(feedback)
        parts.append("")
        parts.append(
            "Please analyze the errors above and generate an improved Dockerfile that fixes these issues."
        )
        parts.append("Focus on the specific errors shown in the feedback.")
        parts.append("")

    if repo_structure:
        parts.append("=" * 80)
        parts.append("REPOSITORY STRUCTURE INFORMATION")
        parts.append("=" * 80)
        parts.append("The following files/directories exist (or don't exist) in this repository:")
        parts.append("")
        for key, exists in repo_structure.items():
            status = "✓ EXISTS" if exists else "✗ DOES NOT EXIST"
            parts.append(f"  {status}: {key}")
        parts.append("")
        parts.append(
            "IMPORTANT: Only COPY files/directories that EXIST. Use conditional COPY or check existence first."
        )
        parts.append('Example: RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi')
        parts.append("")

    parts.append("=" * 80)
    parts.append("SPECIFIC TASK")
    parts.append("=" * 80)
    parts.append(task)
    parts.append("")
    parts.append(
        "REMINDER: Only configure environment variables and install dependencies in Dockerfile. "
        "Do NOT modify any source code."
    )
    parts.append("")
    parts.append(
        "FINAL SAVE RULE: The file env.dockerfile must contain **only** your final Dockerfile text — "
        "full overwrite, never append to prior content."
    )
    parts.append("")
    parts.append(
        "STANDALONE SCRIPT REQUIREMENT: The Dockerfile must ensure the environment supports "
        "running standalone Python scripts directly."
    )

    return "\n".join(parts)


def _load_root_dotenv(project_root: Path) -> None:
    env_path = project_root / ".env"
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env)
    if env_path.exists():
        load_dotenv(env_path, override=True)


def dockerwrite(
    repo_root: Path | str,
    *,
    project_root: Optional[Path] = None,
    feedback: Optional[str] = None,
    model: Optional[str] = None,
    verbose: bool = False,
    claude_args: Optional[List[str]] = None,
) -> int:
    """
    Load ``conf/dockerbuild/write`` and ``prompt/dockerbuild/write``, merge ``.env`` into
    the process environment, then run
    ``claude -p <prompt> [--model ...] --dangerously-skip-permissions ...`` with cwd set
    to ``repo_root``.

    ``model`` is passed to the Claude CLI as ``--model <model>`` (after ``-p``). If omitted,
    the CLI uses its default / ``ANTHROPIC_MODEL`` / settings.

    ``--dangerously-skip-permissions`` is always appended (Claude Code permission prompt skip).

    Omitting mock/API example content (unlike legacy repo-build). Intended to run **after**
    :func:`dockerbuild.init.dockerinit` so ``env.dockerfile`` can be included in the prompt.

    After ``claude`` exits, any legacy ``claude.dockerfile`` is merged into ``env.dockerfile``
    (overwrite) and removed. Then ``FORGE_API_KEY`` / ``FORGE_BASE_URL`` from the project root
    ``.env`` are **injected** as literal ``ENV`` lines (after the first ``FROM``) so
    later ``ENV ...=${FORGE_API_KEY}`` lines resolve. With ``verbose=True``, the final
    ``env.dockerfile`` contents are printed after injection.

    Returns the ``claude`` subprocess exit code (or ``1`` if ``claude`` is missing).
    """
    root = (project_root or PROJECT_ROOT).resolve()
    rroot = Path(repo_root).resolve()

    _load_root_dotenv(root)

    fb = feedback if feedback is not None else os.getenv("DOCKERFILE_FEEDBACK")

    prompt = build_dockerwrite_prompt(root, rroot, feedback=fb)

    if verbose:
        print(paint("1;36", "\n========== LLM exchange =========="), file=sys.stderr)
        log_line("[dockerwrite]", paint("90", "backend:"), paint("36", "Claude CLI (`claude -p`, single user prompt)"))
        log_line("[dockerwrite]", paint("90", "project root:"), paint("32", str(root)))
        log_line("[dockerwrite]", paint("90", "repo (cwd):"), paint("32", str(rroot)))
        model_src = (
            "explicit `model=` → `--model` (overrides CLI default / ANTHROPIC_MODEL)"
            if model
            else "omit `model=` → Claude default / `ANTHROPIC_MODEL` / settings"
        )
        if model:
            log_line("[dockerwrite]", paint("1;33", "[model]"), paint("32", model))
        else:
            log_line(
                "[dockerwrite]",
                paint("1;33", "[model]"),
                paint("90", "(default — set `model=` or ANTHROPIC_MODEL)"),
            )
        print(f"{paint('90', '[model source]')} {model_src}", file=sys.stderr)
        print(
            f"{paint('35', '[system]')} (0 chars)\n"
            f"{paint('90', '(none — `claude -p` does not send a separate system message; instructions are inside the prompt below)')}",
            file=sys.stderr,
        )
        print(
            f"{paint('35', '[user]')} ({len(prompt)} chars, includes templates + repo context)\n"
            f"{_preview(prompt, 1200)}",
            file=sys.stderr,
        )
        log_line(
            "[dockerwrite]",
            paint("90", "claude flags:"),
            paint("36", "--dangerously-skip-permissions"),
        )
        print(paint("34", "---------- spawning claude ----------"), file=sys.stderr)

    extra = list(claude_args or [])
    cmd: List[str] = ["claude", "-p", prompt]
    if model:
        cmd.extend(["--model", model])
    cmd.append("--dangerously-skip-permissions")
    cmd.extend(extra)

    try:
        result = subprocess.run(cmd, env=os.environ, cwd=str(rroot))
        code = int(result.returncode)
    except FileNotFoundError:
        print(
            paint("31", "error: 'claude' command not found. Install Claude CLI and ensure it is in PATH."),
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print(paint("33", "\nInterrupted."), file=sys.stderr)
        return 130

    _normalize_to_env_dockerfile(rroot)
    _inject_project_dotenv_into_env_dockerfile(rroot, root, verbose=verbose)

    if verbose:
        status = paint("32", "ok") if code == 0 else paint("31", f"exit {code}")
        log_line("[dockerwrite]", paint("90", "claude finished:"), status)
        env_p = rroot / "env.dockerfile"
        if env_p.is_file():
            body = env_p.read_text(encoding="utf-8", errors="replace")
            print(
                paint("1;36", "\n========== env.dockerfile (final, after claude) =========="),
                file=sys.stderr,
            )
            print(paint("32", body), file=sys.stderr)
            print(
                paint("1;36", "=============================================================\n"),
                file=sys.stderr,
            )
        else:
            log_line(
                "[dockerwrite]",
                paint("33", "warning:"),
                paint("90", "env.dockerfile not found under repo root after run"),
            )
        print(paint("1;36", "==========================================\n"), file=sys.stderr)

    return code
