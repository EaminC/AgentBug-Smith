"""Train per-repo skill notes, repo-by-repo, for one (agent, train_size).

For a given configuration:

  - call ``utils.split.split`` with mode=repo_disjoint (zero leakage)
    and the requested train_size to obtain the per-repo partition.
  - for each repo in train_repos:
      - clone the repo into a scratch workspace
      - materialise all the repo's issues (train ∪ test) as
        issue.json / patch.diff / f2p.txt bundles
      - invoke the chosen agent wrapper (``agent/run_<agent>.sh``)
        with the prompt from ``utils.train.prompts``; the agent
        writes ``repos/<owner>__<name>.md`` into the skill dir.
  - finalise SKILL.md (from the template) and write manifest.json.

Usage::

    python utils/train/train_skill.py \\
        --agent mini-swe-agent \\
        --train-size 40 \\
        --mode repo_disjoint \\
        --seed 42 \\
        --out agent/skills

    python utils/train/train_skill.py --dry-run --agent openhands \\
        --train-size 20   # print prompts, no agent calls.

The output of a full run for one (agent, train_size) is::

    agent/skills/<agent>/<train_size>/
        SKILL.md                       # the skill itself
        fallback_generic_fix.md        # generated from template
        repos/
            <owner>__<name>.md         # one per trained repo
        manifest.json                  # provenance

Six full runs (2 agents × 3 sizes) populate the whole ``agent/skills/``
tree.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

# Re-use the split module as a library.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))            # utils/
sys.path.insert(0, str(HERE.parent.parent))     # repo root (for `from utils...`)
from utils.split import run as split_mod         # noqa: E402
from utils.train import prompts as prompt_mod    # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

# Conservative ceiling on per-repo agent spend. mini-swe-agent is cheap
# enough that 3 USD is fine; openhands on gpt-4o-mini through a
# third-party gateway has been observed to drift upward quickly, and a
# higher ceiling just gives it more rope to hallucinate.
DEFAULT_COST_LIMIT = 1.5


# ---------------------------------------------------------------------------
# Data plumbing: gather every issue of a repo (train ∪ test) into a scratch
# workspace under issues/<id>/.
# ---------------------------------------------------------------------------
def _issue_dirs_for_repo(index: list[dict], repo: str) -> list[Path]:
    """Return the absolute paths of all issue directories belonging to ``repo``."""
    return [Path(r["path"]) for r in index if r["repo"] == repo]


def _materialise_issues(
    src_dirs: Iterable[Path], dest_root: Path
) -> list[tuple[str, Path]]:
    """Copy each issue dir's payload into ``dest_root/issues/<id>/``.

    Returns a list of ``(issue_id, dest_dir)`` for the prompts to reference.

    Source-dir contents vary across the dataset; we copy whatever is
    available and rename to a stable layout for the agent. The renamed
    set is documented to the agent in the prompt, so a missing
    ``patch.diff`` is recoverable (the issue body + f2p test still tell
    most of the fix story).

    Source name         → dest name         (always)
    ------------------- ----------------------
    issue_<id>.json     → issue.json
    agentsmith_fail2pass_<id>.py
                        → fail2pass_test.py
    generated_patch.diff → patch.diff        (may be absent)
    f2p.txt             → f2p.txt
    summary.json        → summary.json
    agentsmith_stat.json → agentsmith_stat.json
    run.log             → run.log
    env.dockerfile      → env.dockerfile
    """
    out: list[tuple[str, Path]] = []
    for src in src_dirs:
        iid = prompt_mod.issue_id_from_path(src)
        dest = dest_root / "issues" / iid
        dest.mkdir(parents=True, exist_ok=True)

        rename_map = {
            f"issue_{iid}.json": "issue.json",
            f"agentsmith_fail2pass_{iid}.py": "fail2pass_test.py",
            "generated_patch.diff": "patch.diff",
            "f2p.txt": "f2p.txt",
            "summary.json": "summary.json",
            "agentsmith_stat.json": "agentsmith_stat.json",
            "run.log": "run.log",
            "env.dockerfile": "env.dockerfile",
        }
        for src_name, dest_name in rename_map.items():
            src_file = src / src_name
            if not src_file.exists():
                continue
            target = dest / dest_name
            if src_file.resolve() == target.resolve():
                continue
            shutil.copy2(src_file, target)

        # If a patch.diff didn't exist, leave a NOTE so the agent knows.
        if not (dest / "patch.diff").exists():
            (dest / "PATCH_MISSING.txt").write_text(
                "No generated_patch.diff in the source directory for this "
                "issue. The training data for this issue only includes the "
                "issue body (issue.json) and the failing test "
                "(fail2pass_test.py). Distill the fix pattern from those.\n",
                encoding="utf-8",
            )
        out.append((iid, dest))
    return out


def _setup_scratch(
    repo: str, issue_dirs: list[Path], scratch_root: Path
) -> Path:
    """Clone the repo and lay out its issues. Returns the scratch dir."""
    scratch = scratch_root / prompt_mod.safe_repo_name(repo)
    scratch.mkdir(parents=True, exist_ok=True)
    clone_target = scratch / "src"
    if not clone_target.exists():
        subprocess.run(
            ["git", "clone", "--depth=1", f"https://github.com/{repo}.git",
             str(clone_target)],
            check=True,
        )
    _materialise_issues(issue_dirs, scratch)
    # README to orient the agent.
    (scratch / "README.txt").write_text(
        f"Scratch workspace for skill-training run on repo {repo}.\n"
        f"Issues are under issues/<id>/; source tree is under src/.\n",
        encoding="utf-8",
    )
    return scratch


# ---------------------------------------------------------------------------
# Agent invocation — wraps the existing agent/run_<agent>.sh.
# ---------------------------------------------------------------------------
def _agent_run_script(agent: str) -> Path:
    """Return absolute path to the agent's wrapper script."""
    name = "mini" if agent == "mini-swe-agent" else agent
    return REPO_ROOT / "agent" / f"run_{name}.sh"


def _invoke_agent(
    agent: str,
    task: str,
    cwd: Path,
    cost_limit: float = 3.0,
) -> tuple[subprocess.CompletedProcess, str | None]:
    """Run the agent wrapper with the given task in ``cwd``.

    Returns ``(CompletedProcess, conversation_id_or_None)``. The
    conversation id is parsed from the wrapper's stdout. OH
    prints two forms — ``Conversation ID: <id>`` (no hyphens,
    32 hex chars) and ``run openhands --resume <id>`` (UUID with
    hyphens, followed by a trailing sentence). We prefer the
    UUID-with-hyphens form because that's what the on-disk
    conversation directory is named under
    ``~/.openhands/conversations/``.
    """
    import re as _re
    script = _agent_run_script(agent)
    env = os.environ.copy()
    env["COST_LIMIT"] = str(cost_limit)
    result = subprocess.run(
        ["bash", str(script), "-t", task],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    text = result.stdout + "\n" + result.stderr
    conv_id: str | None = None
    # Prefer the UUID-with-hyphens form (matches disk dir name).
    uuid_re = _re.compile(
        r"--resume\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12})"
    )
    m = uuid_re.search(text)
    if m:
        conv_id = m.group(1)
    else:
        # Fall back to the bare hex form.
        hex_re = _re.compile(
            r"Conversation ID:\s*([0-9a-f]{32})"
        )
        m = hex_re.search(text)
        if m:
            conv_id = m.group(1)
    return result, conv_id


def _extract_markdown_from_conversation(
    conv_id: str | None,
    min_chars: int = 200,
) -> str | None:
    """Read the latest OH conversation events and pull out the last
    text content from an ``agent`` ``MessageEvent``, OR the
    ``new_content`` from a successful ``FileEditorObservation``.

    This is our fallback for when the agent couldn't write a file
    (terminal heredoc timeout, missing security_risk on
    file_editor, sandbox-vs-host path mismatch, etc.) but DID
    produce the markdown either as its final message or as the
    body of a file_editor call that the SDK later dropped.

    Returns the markdown text, or ``None`` if no usable content
    was found.
    """
    if not conv_id:
        return None
    conv_dir = Path.home() / ".openhands" / "conversations" / conv_id / "events"
    if not conv_dir.exists():
        return None
    candidates: list[tuple[str, str, str]] = []  # (sort_key, source, text)
    for ev in sorted(conv_dir.glob("event-*.json")):
        if not ev.stat().st_size:
            continue
        try:
            with ev.open() as fh:
                v = json.loads(fh.read())
        except (OSError, json.JSONDecodeError):
            continue
        # Source A: agent MessageEvent with long text.
        if v.get("source") == "agent" and v.get("kind") == "MessageEvent":
            llm = v.get("llm_message") or {}
            content = llm.get("content", [])
            if isinstance(content, list):
                for piece in content:
                    if not isinstance(piece, dict):
                        continue
                    if piece.get("type") == "text":
                        text = piece.get("text", "")
                        if len(text) >= min_chars:
                            candidates.append(
                                (ev.name, "msg", text)
                            )
                            break
        # Source B: environment ObservationEvent for file_editor
        # whose new_content is the markdown.
        if (v.get("source") == "environment"
                and v.get("tool_name") == "file_editor"
                and v.get("kind") == "ObservationEvent"):
            obs = v.get("observation") or {}
            if isinstance(obs, dict) and not obs.get("is_error"):
                nc = obs.get("new_content", "")
                if isinstance(nc, str) and len(nc) >= min_chars:
                    candidates.append(
                        (ev.name + "Z", "file", nc)  # sort after msg
                    )
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][2]


def _retry_with_feedback(
    agent: str,
    repo: str,
    out_path: Path,
    scratch: Path,
    cost_limit: float,
    reasons: list[str],
    issue_titles: list[str],
) -> bool:
    """Second-chance pass: ask the agent to rewrite with the
    validator's feedback appended. The bad output is moved aside
    first so the agent's ``Write`` tool will succeed.
    """
    bad = out_path.with_suffix(".md.hallucinated")
    if bad.exists():
        bad.unlink()
    feedback = (
        "Your previous attempt for this repo was rejected by an "
        "automated validator. Rewriting the same way will be "
        "rejected again. Reasons:\n\n"
        + "\n".join(f"- {r}" for r in reasons)
        + "\n\nTo fix this:\n"
        "1. Open `src/README.md` (or pyproject.toml / package.json) "
        "and copy the repo's actual name from there.\n"
        "2. Open `issues/<id>/issue.json` for at least one issue "
        "and include a worked-example section that quotes the "
        "issue's title verbatim.\n"
        "3. Only mention file paths that you have actually seen in "
        "`src/` or in `issues/<id>/patch.diff`.\n\n"
        "Then overwrite the same output path. Do not add new "
        "paths or invented issue numbers.\n\n"
        "**IMPORTANT — write the file via small append heredocs "
        "to the `terminal` tool, NOT a single big heredoc** "
        "(the OpenHands terminal tool wraps long lines and times "
        "out on >30 s of silence, mangling the file). Pattern:\n\n"
        "    : > \"" + str(out_path) + "\"\n"
        "    cat >> \"" + str(out_path) + "\" <<'RQ4_NOTES_EOF'\n"
        "    <up to 20 lines of markdown>\n"
        "    RQ4_NOTES_EOF\n"
        "    # repeat cat >> for more chunks, then\n"
        "    wc -l \"" + str(out_path) + "\"\n"
    )
    # Strong hint: scratch has exactly N issues; enumerate them so the
    # agent does NOT keep inventing `issues/<n>/issue.json` paths that
    # don't exist (which makes it loop forever in the file_editor tool).
    scratch_issues_dir = scratch / "issues"
    real_ids: list[str] = []
    if scratch_issues_dir.is_dir():
        real_ids = sorted(
            d.name for d in scratch_issues_dir.iterdir()
            if d.is_dir() and d.name.isdigit()
        )
    if real_ids:
        feedback += (
            "\n\n## HARD STOP — there are exactly "
            f"{len(real_ids)} issue(s) in this scratch: "
            f"{', '.join(real_ids)}.\n"
            "Do NOT call `file_editor view issues/<n>/issue.json` for "
            "any `n` not in this list — those paths do not exist and "
            "you will loop forever. Pick one of the listed IDs and "
            "use it directly.\n"
        )
    if issue_titles:
        feedback += "\n\nIssue titles available in this scratch:\n" + \
            "\n".join(f"- {t}" for t in issue_titles[: min(8, len(issue_titles))])
    # Append to a feedback file so the agent sees it even if the
    # CLI doesn't replay it.
    fb_path = scratch / "VALIDATOR_FEEDBACK.txt"
    fb_path.write_text(feedback, encoding="utf-8")
    print(f"  [retry] {repo} with validator feedback "
          f"({len(reasons)} reason(s))")
    # Truncate the cached output if it still exists (it shouldn't).
    if out_path.exists():
        out_path.unlink()
    retry_task = (
        f"Validator rejected your previous output for `{repo}`. "
        f"Read `{fb_path}` for the reasons, then rewrite the file "
        f"at `{out_path}`. Use the same format and sections as "
        "the original prompt (Repo identity, Typical issue shape, "
        "Recurring fix patterns, Files / modules that change most "
        "often, Pitfalls, Test conventions, One concrete worked "
        "example — quoting an issue title verbatim from "
        "`issues/<id>/issue.json`)."
    )
    result, conv_id = _invoke_agent(agent, retry_task, cwd=scratch,
                                     cost_limit=cost_limit)
    if result.returncode != 0:
        print(f"  [err ] {repo} retry exited {result.returncode}")
        return False
    # Same fallback as the first attempt.
    if (not out_path.exists() or out_path.stat().st_size < 200) and conv_id:
        md = _extract_markdown_from_conversation(conv_id)
        if md and len(md) >= 200:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            print(f"  [fix ] {repo} retry recovered {len(md)} chars "
                  f"from agent message")
    if not out_path.exists() or out_path.stat().st_size < 200:
        print(f"  [err ] {repo} retry produced no usable notes file")
        return False
    return True


# ---------------------------------------------------------------------------
# Skill finalisation — assemble SKILL.md, fallback, manifest.
# ---------------------------------------------------------------------------
def _write_skill_md(
    skill_dir: Path, agent: str, train_size: int, repos: list[str]
) -> None:
    template = (HERE / "templates" / "SKILL.template.md").read_text(
        encoding="utf-8")
    repo_bullets = "\n".join(f"- `{r}`" for r in sorted(repos))
    body = template.replace("N training issues across R repos",
                            f"{train_size} training issues across "
                            f"{len(repos)} repos")
    body = body.replace("- `strands-agents`", repo_bullets)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def _write_fallback(skill_dir: Path) -> None:
    src = HERE / "templates" / "fallback_generic_fix.template.md"
    (skill_dir / "fallback_generic_fix.md").write_text(
        src.read_text(encoding="utf-8"), encoding="utf-8")


def _write_manifest(
    skill_dir: Path,
    *,
    agent: str,
    train_size: int,
    mode: str,
    seed: int,
    actual_train_size: int,
    repos: list[str],
    issues_per_repo: dict[str, int],
    single_issue: str | None = None,
) -> None:
    rel_skill_dir = (
        str(skill_dir.relative_to(REPO_ROOT))
        if str(skill_dir).startswith(str(REPO_ROOT))
        else str(skill_dir)
    )
    manifest = {
        "agent": agent,
        "train_size_requested": train_size,
        "train_size_actual": actual_train_size,
        "split_mode": mode,
        "seed": seed,
        "repos_trained": sorted(repos),
        "issues_per_repo": issues_per_repo,
        "total_issues_for_skill": sum(issues_per_repo.values()),
        "skill_dir": rel_skill_dir,
    }
    if single_issue is not None:
        manifest["single_issue"] = single_issue
        manifest["smoke_test"] = True
    (skill_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _extract_repo_description(repo: str, scratch_dir: Path) -> str:
    """Build a short markdown block describing the repo from real inputs.

    Used as the canonical "Repo identity" section of the prompt so
    the agent doesn't have to guess from a repo name. We deliberately
    only cite things we can extract — no LLM paraphrasing here.

    Sources, in order:
      1. ``src/README.md`` first non-empty paragraph (skipping the
         badge line).
      2. ``src/pyproject.toml`` ``[project]`` description /
         ``name`` if README is missing or empty.
      3. ``package.json`` ``description`` field as a last resort.
      4. (NEW) The top-level subdirectories under ``src/`` — this
         is critical for monorepos like strands-agents/sdk-python
         where the actual code lives under ``strands-py/src/...``
         not ``src/...``.

    Returns a markdown bullet list capped at ~10 lines.
    """
    lines: list[str] = []
    src = scratch_dir / "src"

    readme = src / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        # First non-empty, non-badge line that looks like prose.
        # Skip HTML tags, badge lines, anchors, and very short lines.
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("<a", "<img", "<div", "<p", "<span",
                               "![", "|", "<picture")):
                continue
            if "<" in line and ">" in line:
                # HTML-wrapped heading — strip tags.
                import re as _re
                line = _re.sub(r"<[^>]+>", "", line).strip()
            if len(line) < 20:
                continue
            # Strip leading markdown heading / bullets.
            line = line.lstrip("#-* ").strip()
            lines.append(f"- README: {line}")
            break

    pyproject = src / "pyproject.toml"
    if pyproject.exists():
        try:
            data = pyproject.read_text(encoding="utf-8", errors="replace")
        except OSError:
            data = ""
        # Naive parse; we don't want to depend on tomli here.
        in_project = False
        name = desc = None
        for raw in data.splitlines():
            stripped = raw.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_project = stripped == "[project]"
                continue
            if not in_project:
                continue
            if "=" in stripped:
                k, _, v = stripped.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "name" and name is None:
                    name = v
                elif k == "description" and desc is None:
                    desc = v
        if name:
            lines.append(f"- pyproject name: `{name}`")
        if desc:
            lines.append(f"- pyproject description: {desc}")

    pkg = src / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            if data.get("name"):
                lines.append(f"- package.json name: `{data['name']}`")
            if data.get("description"):
                lines.append(f"- package.json description: {data['description']}")

    # Surface the top-level *subdirectories* under src/. For a
    # monorepo like strands-agents/sdk-python this tells the agent
    # that the code lives under strands-py/, not src/ directly.
    if src.exists():
        try:
            top_dirs = sorted(
                p.name + "/"
                for p in src.iterdir()
                if p.is_dir()
                and not p.name.startswith((".", "_", "node_modules"))
                and p.name not in ("docs", "site", "team", "__pycache__")
            )[:8]
            if top_dirs:
                lines.append(
                    "- Top-level subdirs under src/: "
                    f"{top_dirs} (code lives under these)"
                )
        except OSError:
            pass

    if not lines:
        lines.append("- (no description extracted)")
    # Cap to 10 lines.
    return "\n".join(lines[:10])


def _real_paths_in_repo(scratch_dir: Path, limit: int = 2000) -> set[str]:
    """Return a sample of relative paths under src/ that actually exist.

    Used by the validator to detect invented paths in the agent's
    output. We sample because repos can have thousands of files;
    2000 is enough to catch most hallucinations without slowing
    the check. We also include directory paths (so a token like
    ``src/strands/agent/`` is matched even without a file at
    exactly that path).
    """
    src = scratch_dir / "src"
    if not src.exists():
        return set()
    paths: set[str] = set()
    # First pass: directories (cheap).
    for p in src.rglob("*"):
        if p.is_dir():
            try:
                rel = str(p.relative_to(src))
                if rel != ".":
                    paths.add(rel)
            except ValueError:
                continue
    # Second pass: files (capped).
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = str(p.relative_to(src))
        except ValueError:
            continue
        paths.add(rel)
        if len(paths) >= limit + 1000:  # dirs already in set
            break
    return paths


def _looks_like_path(token: str) -> bool:
    """Heuristic: does this token look like a file path?"""
    # Reject obvious garbage: whitespace inside, or markdown table
    # artefacts (leading/trailing pipes or bullets).
    if not token or any(c.isspace() for c in token):
        return False
    if token.startswith(("|", "•", "*", "-")) or token.endswith("|"):
        return False
    # Must contain a slash or backslash, and a dot in the basename,
    # and not look like a URL or markdown link target.
    if "/" not in token and "\\" not in token:
        return False
    if "." not in token.rsplit("/", 1)[-1]:
        return False
    if token.startswith(("http://", "https://", "git@", "ssh://")):
        return False
    return True


def _real_subdirs(scratch_dir: Path) -> list[str]:
    """Return the top-level subdirectory names under ``src/`` that
    look like actual code packages (skip noise like ``docs``,
    ``site``, ``team``, ``test-infra`` only if we have nothing
    better)."""
    src = scratch_dir / "src"
    if not src.exists():
        return []
    SKIP = {".git", ".github", "node_modules", "__pycache__",
            "docs", "site", "team"}
    out: list[str] = []
    for p in sorted(src.iterdir()):
        if not p.is_dir() or p.name.startswith((".", "_")):
            continue
        if p.name in SKIP:
            continue
        out.append(p.name)
    return out


def _auto_fix_invented_paths(
    notes_text: str,
    scratch_dir: Path,
    invented_paths: list[str],
) -> tuple[str, int]:
    """Best-effort path fixer for the common monorepo case where
    the agent writes ``src/strands/agent/agent.py`` but the real
    path is ``strands-py/src/strands/agent/agent.py``.

    Strategy: for each invented path, try (in order):

      1. Look it up verbatim in the real-paths set.
      2. Strip a leading ``src/`` and try prepending each
         top-level subdir under ``src/`` (handles monorepos).
      3. Match on basename — pick the real path whose basename
         matches and whose path-tail overlaps the invented path.

    Returns ``(rewritten_text, num_replacements)``.
    """
    real_paths = _real_paths_in_repo(scratch_dir)
    if not real_paths:
        return notes_text, 0
    real_set = set(real_paths)
    # Also build basename → paths index.
    by_basename: dict[str, list[str]] = {}
    for rp in real_paths:
        by_basename.setdefault(rp.rsplit("/", 1)[-1], []).append(rp)

    subdirs = _real_subdirs(scratch_dir)
    rewrites: dict[str, str] = {}
    for inv in invented_paths:
        if inv in real_set:
            continue  # already real, shouldn't happen
        # Candidate rewrites in priority order.
        candidates: list[str] = []
        # Strip leading src/ and prepend each subdir.
        stripped = inv
        if stripped.startswith("src/"):
            stripped = stripped[4:]
        for sub in subdirs:
            cand = f"{sub}/src/{stripped}"
            if cand in real_set:
                candidates.append(cand)
        # Basename match.
        base = inv.rsplit("/", 1)[-1]
        for real in by_basename.get(base, []):
            if real not in candidates:
                candidates.append(real)
        # Pick the shortest match (less prefix noise).
        if candidates:
            candidates.sort(key=len)
            rewrites[inv] = candidates[0]

    if not rewrites:
        return notes_text, 0
    new_text = notes_text
    n = 0
    for inv, real in rewrites.items():
        # Replace backticked form first.
        bt = f"`{inv}`"
        bt_real = f"`{real}`"
        if bt in new_text:
            new_text = new_text.replace(bt, bt_real)
            n += 1
        # Also replace bare inv (in case it appears outside backticks).
        elif inv in new_text:
            new_text = new_text.replace(inv, real)
            n += 1
    return new_text, n


def _validate_notes_output(
    notes_text: str,
    scratch_dir: Path,
    expected_repo_name: str,
    issue_titles: list[str],
) -> tuple[bool, list[str], list[str]]:
    """Check the notes file for obvious hallucinations.

    Returns ``(ok, list_of_reasons, list_of_invented_paths)``.
    ``invented_paths`` is the list of paths the validator
    flagged — the caller can pass it to
    ``_auto_fix_invented_paths`` to attempt an automatic repair.
    """
    reasons: list[str] = []
    invented_paths: list[str] = []

    # Rule 1: at least one real name for this repo must appear in the
    # output. We accept (case-insensitive substring):
    #   - the slug passed in (e.g. "sdk-python")
    #   - the project name from pyproject.toml / package.json
    #   - the first H1 of src/README.md
    expected_aliases: set[str] = {expected_repo_name.lower()}

    def _add_alias(s: str) -> None:
        s = s.strip().strip('"').strip("'").lower()
        if len(s) >= 3:
            expected_aliases.add(s)

    pyproject = scratch_dir / "src" / "pyproject.toml"
    if pyproject.exists():
        in_project = False
        for line in pyproject.read_text(encoding="utf-8",
                                        errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_project = stripped == "[project]"
                continue
            if in_project and stripped.startswith("name"):
                _, _, v = stripped.partition("=")
                _add_alias(v)
                # also add the part before any dash (e.g.
                # "strands-agents" -> "strands")
                short = v.split("-", 1)[0].split("_", 1)[0]
                _add_alias(short)

    pkg = scratch_dir / "src" / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8",
                                            errors="replace"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            _add_alias(str(data.get("name", "")))

    readme = scratch_dir / "src" / "README.md"
    if readme.exists():
        for raw in readme.read_text(encoding="utf-8",
                                    errors="replace").splitlines():
            line = raw.strip().lstrip("#").strip()
            if 4 <= len(line) <= 80 and "<" not in line:
                _add_alias(line)
                break

    text_lower = notes_text.lower()
    if not any(alias in text_lower for alias in expected_aliases):
        reasons.append(
            f"no repo identifier found in notes "
            f"(looked for: {sorted(expected_aliases)[:5]})"
        )

    # Rule 2: at least one real issue title must appear (loosely).
    # We try multiple granularities — first the title as-is, then
    # the first 2 distinctive words. If neither matches, the
    # agent didn't include any worked example.
    title_signatures: list[set[str]] = []
    for t in issue_titles:
        t_low = t.lower().strip()
        if len(t_low) >= 8:
            title_signatures.append({t_low})
        words = [w.lower().strip("[]():.,!?") for w in t.split()
                 if len(w.strip("[]():.,!?")) >= 4][:3]
        if len(words) >= 2:
            title_signatures.append(set(words[:2]))
    if title_signatures:
        matched_any = False
        for sig in title_signatures:
            if all(w in text_lower for w in sig):
                matched_any = True
                break
        if not matched_any:
            reasons.append(
                "no real issue title found in notes "
                f"(checked {len(title_signatures)} title(s) from inputs)"
            )

    # Rule 3: no invented file paths. We scan backticked tokens for
    # those that look like paths and reject any whose top-3 path
    # segments don't intersect the real repo's paths.
    real_paths = _real_paths_in_repo(scratch_dir)
    # Index real paths by leading segments for fast lookup.
    real_lead_segments: set[tuple[str, ...]] = set()
    for rp in real_paths:
        parts = tuple(rp.split("/")[:3])
        for n in (1, 2, 3):
            if len(parts) >= n:
                real_lead_segments.add(parts[:n])

    invented: list[str] = []
    for token in re.findall(r"`([^`]+)`", notes_text):
        if not _looks_like_path(token):
            continue
        # Strip trailing line/col refs like ":42" or "#L12".
        clean = token.split(":")[0].split("#")[0].rstrip(".,)")
        segs = tuple(clean.split("/")[:3])
        # Accept if ANY of the leading-segment prefixes actually
        # exists in the repo. So `src/strands/agent/agent.py`
        # passes only if there is a `src/strands/agent/` directory
        # under src/. If the model writes `src/foo/bar/baz.py`
        # and `src/foo/` doesn't exist, that's invented.
        accepted = False
        for n in (1, 2, 3):
            if len(segs) >= n and segs[:n] in real_lead_segments:
                accepted = True
                break
        if accepted:
            continue
        # Otherwise the model invented this path.
        invented.append(clean)
    if invented:
        reasons.append(
            f"invented file paths not found in repo: "
            f"{sorted(set(invented))[:5]}"
        )

    return (len(reasons) == 0, reasons, list(dict.fromkeys(invented)))


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------
def train_one_repo(
    *,
    agent: str,
    repo: str,
    issue_dirs: list[Path],
    skill_dir: Path,
    scratch_root: Path,
    cost_limit: float,
    dry_run: bool,
    validate: bool = True,
) -> bool:
    """Train the per-repo notes for one repo. Returns True on success."""
    safe = prompt_mod.safe_repo_name(repo)
    out_path = skill_dir / "repos" / f"{safe}.md"
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"  [skip] {safe}.md already exists")
        return True

    scratch = _setup_scratch(repo, issue_dirs, scratch_root)
    description_block = _extract_repo_description(repo, scratch)
    issue_titles: list[str] = []
    for d in issue_dirs:
        ij = d / "issue.json"
        if ij.exists():
            try:
                issue_titles.append(
                    json.loads(ij.read_text(encoding="utf-8",
                                            errors="replace")).get("title", "")
                )
            except (OSError, json.JSONDecodeError):
                pass
    task = prompt_mod.repo_lessons_prompt(
        repo=repo,
        description="see " + str(scratch / "src" / "README.md"),
        description_block=description_block,
        scratch_dir=str(scratch),
        out_path=str(out_path),
    )

    if dry_run:
        print(f"--- prompt for {repo} ---")
        print(task[:400] + "\n... [truncated]\n")
        # Still write a stub so the manifest can list this repo.
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            f"# {repo} (stub, dry-run)\n\nTraining not run.\n",
            encoding="utf-8",
        )
        return True

    print(f"  [run] {agent} on {repo}  →  {out_path}")
    result, conv_id = _invoke_agent(
        agent, task, cwd=scratch, cost_limit=cost_limit
    )
    if result.returncode != 0:
        print(f"  [err ] {repo} agent exited {result.returncode}")
        print(result.stderr[-400:])
    # OpenHands has two failure modes that look identical from the
    # orchestrator's side: it exits 0 but the file doesn't exist.
    # Mode A: the agent never wrote (file_editor rejected for
    # missing security_risk, or terminal heredoc timed out).
    # Mode B: it wrote fine and we're done.
    # For Mode A, the agent has typically emitted the markdown as
    # its final assistant message — grab it from the conversation.
    if (not out_path.exists() or out_path.stat().st_size < 200):
        if conv_id:
            print(f"  [fix ] {repo} no file on disk; extracting "
                  f"from conv {conv_id[:8]}")
            md = _extract_markdown_from_conversation(conv_id)
            if md and len(md) >= 200:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(md, encoding="utf-8")
                print(f"  [fix ] {repo} recovered {len(md)} chars "
                      f"from agent message")
            else:
                print(f"  [err ] {repo} agent exited but produced no "
                      f"usable message either")
                return False
        else:
            print(f"  [err ] {repo} no file and no conv id to recover")
            return False

    if validate:
        notes_text = out_path.read_text(encoding="utf-8", errors="replace")
        ok, reasons, invented = _validate_notes_output(
            notes_text,
            scratch_dir=scratch,
            expected_repo_name=repo,  # full owner/name
            issue_titles=[t for t in issue_titles if t],
        )
        if not ok:
            # First try a programmatic path-fix (no extra LLM call).
            if invented:
                fixed, n_fixed = _auto_fix_invented_paths(
                    notes_text, scratch, invented,
                )
                if n_fixed:
                    re_ok, re_reasons, _ = _validate_notes_output(
                        fixed,
                        scratch_dir=scratch,
                        expected_repo_name=repo,
                        issue_titles=[t for t in issue_titles if t],
                    )
                    if re_ok:
                        out_path.write_text(fixed, encoding="utf-8")
                        print(f"  [fix ] {repo} auto-rewrote "
                              f"{n_fixed} invented path(s)")
                        print(f"  [ok  ] {repo}: "
                              f"{out_path.stat().st_size} bytes "
                              f"(auto-fixed, validated)")
                        return True
                    # Save the partial fix attempt for inspection.
                    out_path.write_text(fixed, encoding="utf-8")
                    print(f"  [fix ] {repo} auto-rewrote "
                          f"{n_fixed} path(s) but other reasons remain: "
                          f"{re_reasons}")
                    # Continue to retry path with the partial fix in place
                    # (the agent will see the better starting point).
                    reasons = re_reasons
                    notes_text = fixed
            print(f"  [hal ] {repo} flagged by validator: {reasons}")
            # Move the bad output aside and give the agent one
            # retry round with the validator's reasons fed back.
            bad = out_path.with_suffix(".md.hallucinated")
            shutil.move(str(out_path), str(bad))
            if not _retry_with_feedback(
                agent, repo, out_path, scratch,
                cost_limit=cost_limit, reasons=reasons,
                issue_titles=[t for t in issue_titles if t],
            ):
                return False
            # Re-validate the retry; apply auto-fix again if needed.
            notes_text = out_path.read_text(encoding="utf-8",
                                            errors="replace")
            ok2, reasons2, invented2 = _validate_notes_output(
                notes_text,
                scratch_dir=scratch,
                expected_repo_name=repo,
                issue_titles=[t for t in issue_titles if t],
            )
            if not ok2 and invented2:
                fixed2, n_fixed2 = _auto_fix_invented_paths(
                    notes_text, scratch, invented2,
                )
                if n_fixed2:
                    re_ok2, _, _ = _validate_notes_output(
                        fixed2,
                        scratch_dir=scratch,
                        expected_repo_name=repo,
                        issue_titles=[t for t in issue_titles if t],
                    )
                    if re_ok2:
                        out_path.write_text(fixed2, encoding="utf-8")
                        print(f"  [fix ] {repo} retry auto-rewrote "
                              f"{n_fixed2} invented path(s)")
                        print(f"  [ok  ] {repo}: "
                              f"{out_path.stat().st_size} bytes "
                              f"(retry auto-fixed, validated)")
                        return True
            if not ok2:
                print(f"  [hal ] {repo} retry still fails: {reasons2}")
                bad = out_path.with_suffix(".md.hallucinated.2")
                shutil.move(str(out_path), str(bad))
                return False
            print(f"  [ok  ] {repo} retry passed validation "
                  f"({out_path.stat().st_size} bytes)")
            return True
        print(f"  [ok  ] {repo}: {out_path.stat().st_size} bytes "
              f"(validated)")
    else:
        print(f"  [ok  ] {repo}: {out_path.stat().st_size} bytes")
    return True


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--agent", required=True,
                   choices=["mini-swe-agent", "openhands"])
    p.add_argument("--train-size", type=int, required=True,
                   help="Requested train size (will be rounded up by split)")
    p.add_argument("--mode", default="repo_disjoint",
                   choices=["default", "repo_disjoint", "greedy_issue"])
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--index", type=Path, default=REPO_ROOT / "data" / "index.jsonl")
    p.add_argument("--out", type=Path,
                   default=REPO_ROOT / "agent" / "skills",
                   help="Root directory for trained skills")
    p.add_argument("--scratch-root", type=Path,
                   default=Path(tempfile.gettempdir()) / "rq4-skill-train")
    p.add_argument("--cost-limit", type=float, default=DEFAULT_COST_LIMIT,
                   help=f"USD per per-repo agent call (default {DEFAULT_COST_LIMIT})")
    p.add_argument("--dry-run", action="store_true",
                   help="Print prompts only; don't invoke the agent")
    p.add_argument("--no-validate", action="store_true",
                   help="Skip the post-write hallucination validator "
                        "(not recommended; the validator is what "
                        "stops the agent from inventing repo paths).")
    p.add_argument("--repos", nargs="*", default=None,
                   help="Restrict to a subset of repos (for debugging)")
    p.add_argument("--single-issue", default=None,
                   help="Skip the split: train on exactly this single "
                        "issue id (must exist in the index). Smoke-test "
                        "mode for verifying skill generation without "
                        "running the full pipeline.")
    p.add_argument("--single-repo", default=None,
                   help="Required with --single-issue: issue ids are "
                        "not unique across repos, so we need both.")
    args = p.parse_args()

    index = [json.loads(l) for l in args.index.read_text().splitlines() if l.strip()]
    print(f"[idx] {len(index)} issues loaded")

    if args.single_issue:
        # Smoke-test mode: bypass split, train on exactly one issue.
        # Issue IDs are NOT unique across repos (see #data/index.jsonl
        # — the same `issue-974` appears in agentscope-ai/agentscope
        # and in strands-agents/sdk-python). We require --single-repo
        # alongside --single-issue to disambiguate. Falling back to
        # the first match is silently wrong.
        if not args.single_repo:
            sys.exit("--single-issue requires --single-repo "
                     "(issue ids collide across repos)")
        match = [r for r in index
                 if r["id"] == args.single_issue and r["repo"] == args.single_repo]
        if not match:
            sys.exit(f"--single-issue {args.single_issue!r} / "
                     f"--single-repo {args.single_repo!r} not in index")
        target_repo = match[0]["repo"]
        train_repos = [target_repo]
        # Use the smallest achievable "actual train size" = number of
        # issues in this repo, so the manifest is honest about coverage.
        issues_in_repo = [r for r in index if r["repo"] == target_repo]
        summary = {
            "train_size": len(issues_in_repo),
            "train_repos": train_repos,
            "single_issue": args.single_issue,
        }
        print(f"[spl] single-issue={args.single_issue} repo={target_repo} "
              f"effective_train_size={summary['train_size']}")
    else:
        _, _, summary = split_mod.split(
            index, args.train_size, seed=args.seed, mode=args.mode,
        )
        train_repos = summary["train_repos"]
        print(f"[spl] mode={args.mode} req={args.train_size} "
              f"actual={summary['train_size']} repos={len(train_repos)}")

    if args.repos:
        train_repos = [r for r in train_repos if r in set(args.repos)]
        print(f"[spl] restricted to {len(train_repos)} repos via --repos")

    skill_dir = args.out / args.agent / str(args.train_size)
    (skill_dir / "repos").mkdir(parents=True, exist_ok=True)

    issues_per_repo: dict[str, int] = {}
    for repo in sorted(train_repos):
        ids = _issue_dirs_for_repo(index, repo)
        issues_per_repo[repo] = len(ids)
        ok = train_one_repo(
            agent=args.agent,
            repo=repo,
            issue_dirs=ids,
            skill_dir=skill_dir,
            scratch_root=args.scratch_root,
            cost_limit=args.cost_limit,
            dry_run=args.dry_run,
            validate=not args.no_validate,
        )
        if not ok and not args.dry_run:
            print(f"[warn] {repo} failed; continuing with remaining repos")

    _write_skill_md(skill_dir, args.agent, args.train_size, train_repos)
    _write_fallback(skill_dir)
    _write_manifest(
        skill_dir,
        agent=args.agent,
        train_size=args.train_size,
        mode=args.mode,
        seed=args.seed,
        actual_train_size=summary["train_size"],
        repos=train_repos,
        issues_per_repo=issues_per_repo,
        single_issue=getattr(args, "single_issue", None),
    )
    print(f"[done] skill at {skill_dir}")


if __name__ == "__main__":
    main()
