#!/usr/bin/env python3
"""solve.py — drive the agent over the verify pool.

This is the **rollout** driver for Component 6 of RQ4.

Iterate ``split=1`` rows of a per-skill index file, build (or re-use)
a Docker image with the issue's repo at the base SHA, run the agent
against the resulting container *twice* per issue (with and without
the matching ``SKILL.md`` injected), and capture the trajectory and
patch as an artifact bundle that
``AgentBug-Smith/exp/evaluate_f2p.py --patch-mode issue_json`` can
score.

Sub-commands
------------
``solve.py dry-run``
    Walk every targeted row and print what *would* happen: verify
    the index fields, the pool dir, the resolved SKILL.md (if any),
    and the prompt. No LLM is called, no Docker image is built.
    Use this for the pilot when you want to verify the data flow
    without spending cost.

``solve.py rollout``   (a.k.a. the production run)
    Build Docker images, invoke the agent, save trajectories +
    patches + agent logs into
    ``data/verify/runs/<agent>_<train_size>/<repo>__<id>/{with,without}_skill/``.
    Idempotent — already-done (id, skill_mode) runs are skipped.
    Supports ``--resume`` and ``--max-rows N`` for controlled
    progress.

``solve.py status``
    Print per-(key, skill_mode) completion stats: n_total, n_done,
    n_failed, latest mtime. No side effects.

``solve.py score``
    Apply each captured trajectory's patch to a fresh container,
    run the f2p test, record pass/fail. Thin wrapper over
    AgentSmith's ``evaluate_f2p.py``; not implemented in this
    commit (the eval driver lives in ``exp/evaluate_f2p.py``).

Output layout
-------------
::

    data/verify/runs/<agent>_<train_size>/<repo>__<id>/
        image_meta.json                  # {tag, built_at, build_log_tail}
        with_skill/
            prompt.txt                   # what we passed to -t
            trajectory.json              # mini-swe-agent --output
            patch.txt                    # the agent's git diff
            agent.json                   # {cost, exit_code, stdout_tail, ran_at}
            eval_in.json                 # passed to evaluate_f2p.py later
        without_skill/
            ...

Wiring into the pool
--------------------
The verify pool at ``data/verify/_pool/<owner>__<name>__<id>/``
contains exactly three files (``env.dockerfile``, ``issue.json``,
``agentsmith_fail2pass_<NNN>.py``). To produce a working Docker
build context the solver *also* needs the repo's source tree at
the right base SHA. By convention we expect the upstream
``AgentBug-Smith`` checkout at ``~/AgentBug-Smith`` (it already
hosts a handful of repo clones and the build pipeline). The
solver looks for ``$AGENTSMITH_ROOT/<owner>_<name>`` and aborts
with a clear error if not present.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "utils"))

# Reuse the pool-dir helper + audit from build_verify so solver and
# pool can't drift on the (repo, id) → pool-dir mapping.
from verify.build_verify import pool_dir_for  # noqa: E402

VERIFY_ROOT = REPO_ROOT / "data" / "verify"
POOL_DIR = VERIFY_ROOT / "_pool"
RUNS_ROOT = VERIFY_ROOT / "runs"

AGENTSMITH_ROOT = Path(
    os.environ.get("AGENTSMITH_ROOT", str(Path.home() / "AgentBug-Smith"))
)

SKILL_ROOT = REPO_ROOT / "agent" / "skills"
VENV_BIN = REPO_ROOT / "agent" / "venv" / "bin"
MINI_VENV_BIN = REPO_ROOT / "agent" / ".venv" / "bin"

# OpenHands SDK venv (separate from CLI; CLI is at ~/.local/bin/openhands).
# We use the SDK to avoid the CLI's headless-mode quirks (file_editor schema
# mismatch, prompt format drift). The SDK path is what the openhands
# project officially recommends for batch / programmatic use.
OH_SDK_VENV_BIN = REPO_ROOT / "agent" / "openhands-sdk" / ".venv" / "bin"
OH_SDK_PYTHON = OH_SDK_VENV_BIN / "python"

DEFAULT_MODEL = "openai/gpt-4.1-mini"      # served by tu-zi gateway
DEFAULT_COST_LIMIT = 3.0
DEFAULT_WALL_TIMEOUT = 1800       # 30 min per agent run
DEFAULT_DOCKER_BUILD_TIMEOUT = 3600 # 60 min per image build

SUPPORTED_AGENTS = ("mini-swe-agent", "openhands")
SUPPORTED_TRAIN_SIZES = (40, 60, 80)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Row:
    """A single line of an issue_index JSONL file."""
    index_path: Path
    line_no: int
    raw: dict[str, Any]

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def repo(self) -> str:
        return self.raw["repo"]

    @property
    def category(self) -> str:
        return self.raw.get("category", "?")

    @property
    def split(self) -> int:
        return int(self.raw["split"])

    @property
    def verify_dir(self) -> Path:
        p = self.raw["verify_dir"]
        return (REPO_ROOT / p).resolve() if not Path(p).is_absolute() else Path(p)

    @property
    def test_relpath(self) -> str | None:
        return self.raw.get("test_relpath")

    @property
    def base_sha(self) -> str | None:
        return self.raw.get("base_sha")

    @property
    def skill_key(self) -> str:
        """`mini-swe-agent_40` etc., from source_split."""
        ss = self.raw.get("source_split", {})
        return f"{ss.get('agent')}_{ss.get('train_size_requested')}"


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------

def load_rows(index_path: Path, only_test: bool = True) -> list[Row]:
    """Load rows from an issue_index_*.jsonl file.

    With ``only_test=True`` (default) keep only ``split=1`` rows.
    """
    rows: list[Row] = []
    with index_path.open() as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if only_test and int(obj.get("split", -1)) != 1:
                continue
            rows.append(Row(index_path=index_path, line_no=n, raw=obj))
    return rows


def agent_repo_path(repo: str) -> Path:
    """Map ``strands-agents/harness-sdk`` → ``<agentsmith>/data/<owner>_<name>``."""
    if "/" not in repo:
        raise ValueError(f"repo not in owner/name form: {repo!r}")
    owner, name = repo.split("/", 1)
    for base in (AGENTSMITH_ROOT / "data", AGENTSMITH_ROOT):
        p = base / f"{owner}_{name}"
        if p.exists():
            return p
    raise FileNotFoundError(
        f"repo clone not found at {AGENTSMITH_ROOT}/data/{owner}_{name} "
        f"(or {AGENTSMITH_ROOT}/{owner}_{name}). Clone {repo} into "
        f"$AGENTSMITH_ROOT/data/ or set AGENTSMITH_ROOT."
    )


def skill_path(agent: str, train_size: int, *, with_skill: bool) -> Path:
    """Return the SKILL.md (or the generic fallback for the no-skill baseline)."""
    skill_dir = SKILL_ROOT / agent / str(train_size)
    if with_skill:
        p = skill_dir / "SKILL.md"
    else:
        p = skill_dir / "fallback_generic_fix.md"
    if not p.exists():
        raise FileNotFoundError(p)
    return p


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

ISSUE_PROMPT_TEMPLATE = """\
You are a software engineer. A GitHub issue from the repo **{repo}*
has been reproduced in your working tree at `/testbed`. Your task is to
make the **minimum source-code change** that fixes the issue, **without
modifying any test file**.

## Issue

**Title:** {title}

**Body:**

```
{body}
```

## Test

The fail-to-pass test that must pass after your fix is:

```
{test_relpath}
```

A copy of that test has already been installed at `tests/{test_filename}`
for you — do **not** edit it.

## Submission

When you are done, run `git diff > /testbed/patch.txt` and verify that
`patch.txt` contains only the source files you intended to change.

Then submit with EXACTLY this command (must be its own step, no `&&`):

```
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat /testbed/patch.txt
```

## Tools preference (CRITICAL — read first)

Your working directory IS the testbed repo (a git checkout of the upstream
project at the bug's base commit). Edit source files in place; do not
clone, copy, or re-init a fresh git repo.

**Use the bash tool for ALL edits.** Example workflows:

```bash
# View the file with line numbers
nl -ba src/foo/bar.py | sed -n '40,60p'

# Edit a Python function (safer than file_editor)
python3 - <<'PY'
import re, pathlib
p = pathlib.Path('src/foo/bar.py')
src = p.read_text()
src = src.replace('old_block', 'new_block', 1)
p.write_text(src)
PY

# Verify the change
git diff --stat
git diff src/foo/bar.py | head -80
```

Do NOT use the `file_editor` / `str_replace_editor` tool — its
`security_risk` schema is missing from the runtime you're running on and
will reject every call. Bash is fully equivalent and works.

When all edits are in place, capture the diff and submit:

```bash
git diff > patch.txt
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt
```

(Note: `patch.txt` is the relative path — the cwd is the repo root.)
"""


def build_prompt(row: Row, *, with_skill: bool) -> tuple[str, Path]:
    """Return ``(prompt_text, skill_path_resolved)``.

    ``with_skill=False`` returns the generic fallback so the prompt
    is still intelligible without per-repo guidance.
    """
    ss = row.raw.get("source_split", {})
    agent = ss.get("agent") or "mini-swe-agent"
    train_size = int(ss.get("train_size_requested") or 40)
    skill = skill_path(agent, train_size, with_skill=with_skill)

    issue = json.loads((row.verify_dir / "issue.json").read_text())
    title = issue.get("title", row.id)
    body = issue.get("body") or ""
    test_filename = Path(row.test_relpath or f"tests/agentsmith_fail2pass_{row.id.split('-')[1]}.py").name

    prompt = ISSUE_PROMPT_TEMPLATE.format(
        repo=row.repo,
        title=title,
        body=body,
        test_relpath=row.test_relpath or "(not provided)",
        test_filename=test_filename,
    )

    if with_skill:
        skill_text = skill.read_text()
        prompt = f"<skill>\n{skill_text}\n</skill>\n\n{prompt}"

    return prompt, skill


# ---------------------------------------------------------------------------
# Old helper stubs removed in favor of build_one_image / run_one_agent /
# extract_patch below (see rollout section). Keeping nothing here.
# ---------------------------------------------------------------------------


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Pilot driver
# ---------------------------------------------------------------------------

def dry_run_row(row: Row, *, with_skill: bool) -> dict[str, Any]:
    """Print every input the solver has for a single (row, skill_mode).

    No Docker, no agent — purely a data-flow sanity check.
    """
    prompt, skill = build_prompt(row, with_skill=with_skill)
    v = row.verify_dir
    return {
        "id": row.id,
        "repo": row.repo,
        "category": row.category,
        "split": row.split,
        "skill_key": row.skill_key,
        "with_skill": with_skill,
        "skill_path": str(skill.relative_to(REPO_ROOT)),
        "skill_chars": len(skill.read_text()),
        "verify_dir": str(v.relative_to(REPO_ROOT)),
        "pool_files": sorted(p.name for p in v.iterdir() if p.is_file()),
        "test_relpath": row.test_relpath,
        "base_sha": row.base_sha,
        "issue_title": json.loads((v / "issue.json").read_text()).get("title"),
        "prompt_chars": len(prompt),
        "prompt_head": prompt[:240].replace("\n", " ⏎ "),
    }


def fmt_dry(out: dict[str, Any]) -> str:
    lines = [
        f"  ┌─ pilot ───────────────────────────────────────────────────────",
        f"  │ id           : {out['id']}",
        f"  │ repo         : {out['repo']}",
        f"  │ category     : {out['category']}",
        f"  │ skill        : {out['skill_key']}  with_skill={out['with_skill']}",
        f"  │ SKILL.md     : {out['skill_path']} ({out['skill_chars']} chars)",
        f"  │ verify_dir   : {out['verify_dir']}",
        f"  │ pool files   : {out['pool_files']}",
        f"  │ base_sha     : {out['base_sha']}",
        f"  │ test         : {out['test_relpath']}",
        f"  │ issue_title  : {out['issue_title']!r}",
        f"  │ prompt_chars : {out['prompt_chars']}",
        f"  │ prompt head  : {out['prompt_head']}",
        f"  └──────────────────────────────────────────────────────────────",
    ]
    return "\n".join(lines)


def cmd_dry_run(rows: Iterable[Row]) -> int:
    for row in rows:
        for with_skill in (True, False):
            out = dry_run_row(row, with_skill=with_skill)
            print(fmt_dry(out))
    return 0


# ---------------------------------------------------------------------------
# Rollout orchestration (real runs)
# ---------------------------------------------------------------------------

@dataclass
class RunSpec:
    """A single unit of work: one row × one skill_mode."""
    row: Row
    with_skill: bool
    out_dir: Path            # data/verify/runs/<key>/<id>/{with,without}_skill/
    image_tag: str
    is_done: bool = False
    is_failed: bool = False


def spec_for_row(row: Row, *, with_skill: bool) -> RunSpec:
    ss = row.raw.get("source_split", {})
    agent = ss.get("agent") or "mini-swe-agent"
    train_size = ss.get("train_size_requested") or "?"
    safe_repo = row.repo.replace("/", "__")
    key = f"{agent}_{train_size}"
    # Both skill modes share ONE image (image is the repo+test at base
    # SHA; the skill only changes the prompt). Single tag → single
    # build, reused by both with/without runs.
    # Docker tag must be lowercase; repo names like ``crewAIInc/crewAI``
    # contain upper-case chars that the daemon rejects.
    tag = f"rq4-{safe_repo.lower()}-{row.id}-{train_size}"
    out_dir = (
        RUNS_ROOT / key / f"{safe_repo}__{row.id}"
        / ("with_skill" if with_skill else "without_skill")
    )
    return RunSpec(row=row, with_skill=with_skill, out_dir=out_dir, image_tag=tag)


def spec_is_done(spec: RunSpec) -> bool:
    """A spec is done iff patch.txt exists and agent.json says exit_code==0.

    Note: a cost-1+ step_limit-or-time exceeded exit is also considered
    done if patch.txt is non-empty (the agent did finish; we still score
    whatever patch it produced).
    """
    patch = spec.out_dir / "patch.txt"
    agent_log = spec.out_dir / "agent.json"
    return patch.exists() and patch.stat().st_size > 0 and agent_log.exists()


def spec_is_failed(spec: RunSpec) -> bool:
    sentinel = spec.out_dir / "_failed.json"
    return sentinel.exists()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_lock_path(repo: str) -> Path:
    """Per-repo lock file to serialize concurrent builds.

    Multiple solve.py workers may target the same upstream repo clone
    (e.g. when running a batch over many issues in one repo). Without
    serialization, ``git checkout`` races on ``.git/index.lock`` and
    the build fails. The lock is held only during the ``build_one_image``
    step; agents themselves do not need it because each agent invocation
    is independent of git state once the image is built.
    """
    safe = repo.replace("/", "__").replace(" ", "_")
    return Path("/tmp") / f"rq4_build_lock_{safe}.lock"


def build_one_image(spec: RunSpec) -> tuple[bool, str]:
    """Build a Docker image for a single row, install pool files into the
    upstream repo clone, and tag it.

    The upstream repo at ``$AGENTSMITH_ROOT/<owner>_<name>`` is checked
    out at the row's base SHA first. If the clone is dirty (e.g. a
    previous run left state), we force a clean working tree by
    ``git reset --hard`` after the checkout.
    """
    repo_dir = agent_repo_path(spec.row.repo)
    if not spec.row.base_sha:
        return False, f"row {spec.row.id} has no base_sha"

    lock = _build_lock_path(spec.row.repo)
    lock_fd = open(lock, "w")
    try:
        # Block until no other worker is building against this repo.
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

        # Clean up any stale lock file the previous worker may have left.
        stale_lock = repo_dir / ".git" / "index.lock"
        if stale_lock.exists():
            try:
                stale_lock.unlink()
            except OSError:
                pass

        # Always start from a clean working tree — the dockerfile install
        # step and the previous run may have left unstaged changes, and
        # ``git checkout <base_sha>`` will refuse to proceed otherwise.
        subprocess.run(
            ["git", "-C", str(repo_dir), "reset", "--hard", "HEAD"],
            capture_output=True, text=True, timeout=60,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "clean", "-fd"],
            capture_output=True, text=True, timeout=60,
        )
        rc = subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", spec.row.base_sha],
            capture_output=True, text=True, timeout=60,
        )
        if rc.returncode != 0:
            return False, f"git checkout {spec.row.base_sha} failed: {rc.stderr[:500]}"
        rc = subprocess.run(
            ["git", "-C", str(repo_dir), "reset", "--hard", spec.row.base_sha],
            capture_output=True, text=True, timeout=60,
        )
        if rc.returncode != 0:
            return False, f"git reset --hard failed: {rc.stderr[:500]}"

        # Install the pool's dockerfile + f2p test.
        pool_dockerfile = spec.row.verify_dir / "env.dockerfile"
        if pool_dockerfile.exists():
            shutil.copy2(pool_dockerfile, repo_dir / "env.dockerfile")
        if spec.row.test_relpath:
            test_filename = Path(spec.row.test_relpath).name
            src_test = next(spec.row.verify_dir.glob("agentsmith_fail2pass_*.py"), None)
            if src_test:
                (repo_dir / "tests").mkdir(exist_ok=True)
                shutil.copy2(src_test, repo_dir / "tests" / test_filename)

        # Build.
        rc = subprocess.run(
            ["docker", "build", "-t", spec.image_tag, "-f", "env.dockerfile", "."],
            cwd=repo_dir, capture_output=True, text=True,
            timeout=DEFAULT_DOCKER_BUILD_TIMEOUT,
        )
        ok = rc.returncode == 0
        log = (rc.stdout + "\n" + rc.stderr)[-3000:]
        return ok, log
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()


def run_one_agent(spec: RunSpec, prompt: str, *,
                  model: str, cost_limit: float) -> dict[str, Any]:
    """Invoke the agent against the built image.

    Returns a dict with ``exit_code``, ``cost``, ``stdout_tail``,
    ``stderr_tail``, ``ran_at``. Saves prompt + trajectory + agent log
    to ``spec.out_dir``.
    """
    # Source the tu-zi gateway credentials from agent/config/.env.
    # This file may not be sourced in the parent shell (e.g. nohup), so
    # we load it explicitly into os.environ here so that both the Python
    # subprocess env and the bash-command subprocess see the credentials.
    _dotenv_path = REPO_ROOT / "agent" / "config" / ".env"
    if _dotenv_path.exists():
        for _line in _dotenv_path.read_text().splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#"):
                continue
            if "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

    spec.out_dir.mkdir(parents=True, exist_ok=True)
    (spec.out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    agent_name = spec.row.raw.get("source_split", {}).get("agent") or "mini-swe-agent"
    env = {
        **os.environ,
        "OPENAI_API_BASE": os.environ.get("TUZI_BASE_URL", ""),
        "OPENAI_API_KEY":  os.environ.get("TUZI_API_KEY", ""),
        # mini-swe-agent checks MSWEA_CONFIGURED to skip its setup wizard.
        # We set this here for defense-in-depth even though the docker-run
        # helper also enforces it.
        "MSWEA_CONFIGURED": "1",
        "MSWEA_COST_TRACKING": "ignore_errors",
    }

    if agent_name == "mini-swe-agent":
        # Two execution paths are supported:
        #
        #   1. Inner docker class — ``mini-swe-agent --environment-class docker``.
        #      This makes mini launch its own docker container from
        #      ``spec.image_tag`` (the testbed image we built). The container
        #      is ``--rm``, so all of the agent's edits are LOST on exit;
        #      we recover the patch via the trajectory's ``git diff``
        #      tool output, which is brittle (truncates on large diffs)
        #      and was the cause of 29/46 ``corrupt patch`` errors in our
        #      pilot-20 run.
        #
        #   2. Outer docker run (alfin06's pattern) — we ``docker run --rm``
        #      our testbed image with the upstream repo mounted at /app
        #      and the spec out_dir mounted at /output. The agent's edits
        #      are written to the mount, so we recover the patch via
        #      ``git add -A && git diff`` on the host after the run.
        #
        # Default to (2); fall back to (1) if the mount fails.
        repo_dir = agent_repo_path(spec.row.repo)
        result = _run_mini_swe_agent_docker_run(
            spec, prompt,
            repo_dir=repo_dir, image_tag=spec.image_tag,
            model=model, cost_limit=cost_limit, env=env,
        )
        if (result.get("exit_code") != 0
                and "OCI runtime exec" in (result.get("stderr_tail") or "")):
            # Fallback for environments that block `docker run --rm`.
            result = _run_mini_swe_agent_via_mini_docker(
                spec, prompt,
                image_tag=spec.image_tag,
                model=model, cost_limit=cost_limit, env=env,
            )
    elif agent_name == "openhands":
        # OpenHands has two execution paths:
        #
        #   1. CLI   — ``openhands --headless --override-with-envs --yolo -t <prompt>``.
        #              The CLI is what the OpenHands team ships in their installer;
        #              it goes through a frontend that has known headless-mode
        #              quirks (file_editor schema mismatch, prompt-format drift).
        #              That's why our 6-combo pilot produced 0 patches.
        #
        #   2. SDK   — ``openhands-sdk`` Python package + ``openhands-tools``
        #              (CodeActAgent, LocalWorkspace, LocalConversation). This is
        #              the path the OpenHands project officially recommends for
        #              batch use; it gives explicit control over the tool registry
        #              and ``max_iteration_per_run`` (60 by default — matching
        #              alfin06's reference script).
        #
        # Default to SDK; fall back to CLI only if the SDK venv is missing
        # (so we don't break a half-installed machine).
        repo_dir = agent_repo_path(spec.row.repo)
        sdk_bin = OH_SDK_VENV_BIN / "python"
        if sdk_bin.exists():
            result = _run_openhands_sdk(
                spec, prompt, repo_dir=repo_dir,
                model=model, cost_limit=cost_limit, env=env,
            )
            # Fallback: if SDK returned exit_code != 0 with "module not found"
            # (e.g. SDK install broke mid-flight), try the CLI once.
            if result["exit_code"] != 0 and "No module named" in (result.get("stderr_tail") or ""):
                result = _run_openhands_cli(
                    spec, prompt, repo_dir=repo_dir,
                    model=model, cost_limit=cost_limit, env=env,
                )
        else:
            result = _run_openhands_cli(
                spec, prompt, repo_dir=repo_dir,
                model=model, cost_limit=cost_limit, env=env,
            )
    else:
        return {"agent": agent_name, "exit_code": -1,
                "stderr_tail": f"unknown agent {agent_name!r}", "ran_at": _now()}

    (spec.out_dir / "agent.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _run_openhands_sdk(spec: RunSpec, prompt: str, *,
                        repo_dir: Path, model: str,
                        cost_limit: float, env: dict) -> dict[str, Any]:
    """Run OpenHands via the official Python SDK (CodeActAgent).

    The agent operates on a :class:`LocalWorkspace` rooted at
    ``repo_dir`` (the upstream repo clone at the row's base SHA).
    After the agent finishes, we extract the patch via
    ``git add -A --intent-to-add && git diff`` from that workspace —
    which is exactly what alfin06's reference script does. This bypasses
    the agent's self-reported ``git diff`` output (which used to be the
    cause of CLI's file_editor / patch.txt bugs).

    ``max_iteration_per_run=60`` matches alfin06's default; the
    OpenHands README recommends 30-100 for SWE-bench style tasks.
    """
    sdk_python = OH_SDK_PYTHON
    # Driver script: imports SDK, runs conversation, extracts patch.
    driver = REPO_ROOT / "utils" / "verify" / "_openhands_sdk_driver.py"
    cmd = [
        str(sdk_python), str(driver),
        "--workspace", str(repo_dir),
        "--model", model,
        "--max-iterations", "60",
        "--prompt", prompt,
        "--out-dir", str(spec.out_dir),
        "--cost-limit", str(cost_limit),
    ]
    # Pass LLM credentials via env (don't bake into CLI).
    oh_env = {
        **env,
        "LLM_API_KEY": env.get("OPENAI_API_KEY", ""),
        "LLM_BASE_URL": env.get("OPENAI_API_BASE", ""),
        "OPENHANDS_SUPPRESS_BANNER": "1",
    }
    proc = subprocess.run(
        cmd,
        cwd=str(repo_dir),
        capture_output=True, text=True, timeout=DEFAULT_WALL_TIMEOUT,
        env=oh_env,
    )
    return {
        "agent": "openhands-sdk",
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ran_at": _now(),
        "trajectory_path": str((spec.out_dir / "trajectory.json").relative_to(REPO_ROOT))
                            if (spec.out_dir / "trajectory.json").exists() else None,
    }


def _run_openhands_cli(spec: RunSpec, prompt: str, *,
                       repo_dir: Path, model: str,
                       cost_limit: float, env: dict) -> dict[str, Any]:
    """Fallback: the OpenHands CLI (``openhands --headless --yolo``).

    Kept around because the SDK install requires network access; if
    the SDK venv isn't present, this lets us still run a rollout.
    """
    repo_dir_str = str(repo_dir)
    cli_bin = (
        str(REPO_ROOT / "agent" / "openhands-config" / ".venv" / "bin")
        if (REPO_ROOT / "agent" / "openhands-config" / ".venv").exists()
        else (shutil.which("openhands") or "openhands")
    )
    oh_proc = subprocess.run(
        [cli_bin, "--headless", "--override-with-envs", "--yolo", "-t", prompt],
        cwd=repo_dir_str,
        capture_output=True, text=True, timeout=DEFAULT_WALL_TIMEOUT,
        env=env,
    )
    host_patch = Path(repo_dir_str) / "patch.txt"
    if host_patch.exists():
        content = host_patch.read_text()
        (spec.out_dir / "patch.txt").write_text(content)
    return {
        "agent": "openhands-cli",
        "exit_code": oh_proc.returncode,
        "stdout_tail": oh_proc.stdout[-2000:],
        "stderr_tail": oh_proc.stderr[-2000:],
        "ran_at": _now(),
        "trajectory_path": None,
    }


def _run_mini_swe_agent_docker_run(spec: RunSpec, prompt: str, *,
                                    repo_dir: Path, image_tag: str,
                                    model: str, cost_limit: float,
                                    env: dict) -> dict[str, Any]:
    """Run mini-swe-agent via ``docker run --rm -v workspace:/app ...``.

    Pattern follows alfin06's ``run_mini_swe_agent_batch.py`` line
    367-381: the testbed image (built by ``build_one_image``) is
    launched as a container with the upstream repo mounted at /app
    and the spec out_dir mounted at /output. The agent's edits go to
    the host workspace (via the bind mount), so we can extract the
    patch with ``git add -A && git diff`` after the container exits.

    This avoids the inner ``--environment-class docker`` path that
    silently discards the agent's edits when ``--rm`` destroys the
    container. The inner path was the cause of 29/46 ``corrupt patch``
    errors in our pilot-20 run.
    """
    out_dir = spec.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Environment variables to pass through to the container.
    # OPENAI_* go via the host env; MSWEA_* are peer-style hints that
    # mini-swe-agent reads to suppress config prompts.
    #
    # We also force MSWEA_CONFIGURED=1 even if the parent shell doesn't
    # have it set — the agent's setup wizard checks this env var and
    # prompts for stdin if it's missing, which would deadlock our
    # batch driver.
    fwd_env_keys = [
        "OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_BASE_URL",
        "MSWEA_CONFIGURED", "MSWEA_COST_TRACKING",
        "FORGE_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
        "TAVILY_API_KEY", "GITHUB_TOKEN",
    ]
    # Ensure MSWEA_CONFIGURED is "1" — never None, never empty.
    env_augmented = {
        **env,
        "MSWEA_CONFIGURED": env.get("MSWEA_CONFIGURED") or "1",
        "MSWEA_COST_TRACKING": env.get("MSWEA_COST_TRACKING") or "ignore_errors",
    }
    docker_env_args: list[str] = []
    for k in fwd_env_keys:
        v = env_augmented.get(k) or os.environ.get(k)
        if v:
            docker_env_args.extend(["-e", f"{k}={v}"])

    # mini-swe-agent isn't installed in the testbed image (the image is
    # the bare repo + deps; the agent binary lives in the host venv at
    # agent/.venv). We need to use the container's Python interpreter
    # to run it (the host venv is macOS, the container is linux), so we
    # install mini-swe-agent inside the container at runtime via pip.
    #
    # Mounts:
    #   - repo_dir   → /testbed   (the upstream repo at base_sha; agent
    #                              writes here via the bind mount, and
    #                              we recover the patch with git diff)
    #   - out_dir    → /output    (trajectory.json goes here)
    #   - mini_src   → /mini-src  (the mini-swe-agent source tree, so
    #                              the installed package can be edited
    #                              without re-installing)
    #
    # The swebench.yaml config lives on the HOST path, but inside the
    # container the same file is at /mini-src/src/.../swebench.yaml.
    # We use the container path so mini can find it.
    mini_src = REPO_ROOT / "agent" / "mini-swe-agent"
    env_file = REPO_ROOT / "agent" / "config" / ".env"
    config_in_container = "/mini-src/src/minisweagent/config/benchmarks/swebench.yaml"
    # swebench.yaml sets model_kwargs.drop_params and parallel_tool_calls but
    # NOT api_base. Without it, LiteLLM falls back to the OpenAI default
    # (api.openai.com), which doesn't accept our tu-zi gateway key. Inject
    # api_base from OPENAI_API_BASE so the LLM call goes to the tu-zi gateway.
    # Source .env so bash sees the credentials (the Python subprocess env=
    # is separate from the bash shell env).
    api_base_val = env_augmented.get('OPENAI_API_BASE') or os.environ.get('TUZI_BASE_URL') or ''
    api_base_arg = f"-c model.model_kwargs.api_base={api_base_val}" if api_base_val else ""
    cmd = [
        "docker", "run", "--rm", "--network=host",
        *docker_env_args,
        "-v", f"{repo_dir}:/testbed",
        "-v", f"{out_dir}:/output",
        "-v", f"{mini_src}:/mini-src",
        "-v", f"{env_file}:/mini-src/.env:ro",
        "-w", "/testbed",
        image_tag,
        "bash", "-c",
        # 1) source .env so OPENAI_API_KEY and OPENAI_API_BASE are set for
        #    pip install and the mini agent's LiteLLM calls
        # 2) install mini-swe-agent into the container's site-packages
        # 3) override its import to use the bind-mounted source so we
        #    don't have to re-install on every config tweak
        # 3) drop the empty mini.yaml override (it's intentionally
        #    empty in our setup; passing its host path would fail
        #    inside the container).
        # 4) swebench.yaml defaults environment_class=docker which
        #    would try to spin a sub-container inside our container.
        #    We're already inside the testbed image — use the local
        #    env class so it just runs commands via subprocess.
        #    cwd=/testbed matches the bind-mounted host repo.
        # 5) swebench.yaml doesn't set api_base; without it LiteLLM
        #    falls back to api.openai.com which rejects our tu-zi key.
        #    Inject api_base into model.model_kwargs so the call goes
        #    to the tu-zi gateway.
        ("set -a && . /mini-src/.env && set +a && "
         "pip install --quiet --no-cache-dir 'mini-swe-agent==2.4.6' && "
         "PYTHONPATH=/mini-src/src:$PYTHONPATH "
         "python3 -m minisweagent.run.mini "
         f"-c {config_in_container} "
         f"{api_base_arg} "
         f"--model {model} "
         f"--cost-limit {cost_limit} "
         "--exit-immediately --yolo "
         "-c environment.environment_class=local "
         "-c environment.cwd=/testbed "
         f"-t {shlex.quote(prompt)} "
         "--output /output/trajectory.json"),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_dir),
        capture_output=True, text=True, timeout=DEFAULT_WALL_TIMEOUT,
        env=env,
    )

    # Extract patch from the host workspace via ``git diff``.
    # The bind-mount means whatever the agent wrote is now in repo_dir.
    # Exclude files we added during build (env.dockerfile and the
    # agentsmith fail-to-pass test) — those are build artifacts, not
    # agent edits.
    patch_text = ""
    try:
        subprocess.run(
            ["git", "-C", str(repo_dir), "add", "-A", "--intent-to-add"],
            capture_output=True, text=True, timeout=60,
        )
        # Exclude:
        #   - env.dockerfile: build artifact added before agent runs.
        #   - tests/agentsmith_*: the agentsmith fail-to-pass test.
        #   - *.db / *.sqlite*: agent may create a DB while testing.
        #   - patch.txt: the agent's own patch file (created by `git diff > patch.txt`).
        #   - *.log: agent test logs.
        #   - test_runs/: mini-swe-agent creates this during testing.
        #   - .config/: agent config directory.
        diff_proc = subprocess.run(
            ["git", "-C", str(repo_dir), "diff",
             "--", ".",
             ":!env.dockerfile",
             ":!tests/agentsmith_*",
             ":!*.db", ":!*.sqlite", ":!*.sqlite3",
             ":!patch.txt",
             ":!*.log",
             ":!test_runs",
             ":!.config",
             # Common scratch / reproduction files agents create
             ":!repro*.py", ":!reproduce*.py",
             ":!scratch*.py",
             ":!test_repro*.py",
             ":!patch_*.py",
             ":!debug_*.py",
             ":!tmp_*.py",
             ":!result.log",
             ":!verify_*.py",
             ":!check_*.py",
             ],
            capture_output=True, text=True, timeout=60,
        )
        patch_text = diff_proc.stdout or ""
    except Exception as e:
        patch_text = f"# git diff failed: {e}\n"

    if patch_text.strip():
        (out_dir / "patch.txt").write_text(patch_text, encoding="utf-8")

    return {
        "agent": "mini-swe-agent-docker",
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ran_at": _now(),
        "trajectory_path": str((out_dir / "trajectory.json").relative_to(REPO_ROOT))
                            if (out_dir / "trajectory.json").exists() else None,
    }


def _run_mini_swe_agent_via_mini_docker(spec: RunSpec, prompt: str, *,
                                        image_tag: str,
                                        model: str, cost_limit: float,
                                        env: dict) -> dict[str, Any]:
    """Fallback: original mini-swe-agent ``--environment-class docker``.

    Kept for environments that don't allow bind-mounting the host
    workspace into a docker container. Patches are recovered from the
    trajectory's ``git diff`` tool output (best effort).
    """
    traj_path = spec.out_dir / "trajectory.json"
    proc = subprocess.run(
        [
            str(MINI_VENV_BIN / "mini"),
            "-c", str(REPO_ROOT / "agent" / "mini-swe-agent" / "src"
                      / "minisweagent" / "config" / "benchmarks" / "swebench.yaml"),
            "-c", str(REPO_ROOT / "agent" / "config" / "mini.yaml"),
            "--model", model,
            "--cost-limit", str(cost_limit),
            "--exit-immediately",
            "--yolo",
            "--environment-class", "docker",
            "-c", f"environment.image={image_tag}",
            "--output", str(traj_path),
            "-t", prompt,
        ],
        cwd=str(REPO_ROOT / "agent" / "mini-swe-agent"),
        capture_output=True, text=True, timeout=DEFAULT_WALL_TIMEOUT,
        env=env,
    )
    return {
        "agent": "mini-swe-agent",
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
        "ran_at": _now(),
        "trajectory_path": str(traj_path.relative_to(REPO_ROOT))
                            if traj_path.exists() else None,
    }


def _strip_app_prefix(path: str) -> str:
    """Strip ``/app/`` from a path. Mini operates on the repo mounted
    at ``/app``; ``git apply`` against the host repo needs repo-relative
    paths. Also strips ``b/`` from diff-style paths (``b/X → X``).
    """
    p = path.strip()
    if p.startswith("/app/"):
        p = p[len("/app/"):]
    # Strip leading "b/" from diff-style paths (e.g. "b/A2A/wrapper.py → A2A/wrapper.py")
    if p.startswith("b/"):
        p = p[2:]
    return p


def _normalize_diff_line(line: str) -> str:
    """Normalize a single diff header line for git-format output.

    - ``--- /app/.../X.py.bak`` → ``--- a/<stripped>/X.py``
    - ``+++ /app/.../X.py``     → ``+++ b/<stripped>/X.py``
    """
    if line.startswith("--- "):
        rest = line[4:].split("\t", 1)[0]
        rest = _strip_app_prefix(rest)
        rest = rest.removesuffix(".bak")
        return f"--- a/{rest}"
    if line.startswith("+++ "):
        rest = line[4:].split("\t", 1)[0]
        rest = _strip_app_prefix(rest)
        return f"+++ b/{rest}"
    return line


def _submission_to_git_diff(submission: str) -> str | None:
    """Convert mini's ``--- file.bak / +++ file`` submission to git format.

    mini's last assistant message contains a unified diff against a
    ``.bak`` snapshot the agent made at task start — not a ``git diff``
    header. ``git apply`` rejects this because:

      * the file path is absolute (``/app/src/...``) instead of
        repo-relative (``src/...``),
      * there's no ``diff --git a/X b/X`` header,
      * the ``---`` side references ``X.py.bak``.

    We rewrite each ``+++ path`` header into a git-format block::

        diff --git a/<path> b/<path>
        --- a/<path>
        +++ b/<path>
        <body unchanged>

    where ``<path>`` has had ``/app/`` stripped and ``.bak`` removed.
    Hunk body (``@@ ... @@`` and below) is preserved verbatim.

    Returns None if the submission has no ``+++ path`` header (so
    callers can fall through to other extractors).
    """
    if not submission:
        return None
    if "diff --git " in submission and "/app/" not in submission and " a/b/" not in submission:
        # Already in git format; nothing to do.
        return submission

    lines = submission.split("\n")
    # Detect whether at least one "+++" path exists.
    paths = [ln[4:].strip().split("\t", 1)[0]
             for ln in lines if ln.startswith("+++ ")]
    paths = [p for p in paths if p]
    if not paths:
        return None

    # Walk lines, flushing a git-format block each time we hit "+++ ".
    out_chunks: list[str] = []
    cur_path = None
    cur_lines: list[str] = []
    for ln in lines:
        if ln.startswith("+++ "):
            if cur_path is not None:
                stripped = _strip_app_prefix(cur_path)
                out_chunks.append(f"diff --git a/{stripped} b/{stripped}")
                out_chunks.append(f"--- a/{stripped}")
                for cl in cur_lines:
                    out_chunks.append(_normalize_diff_line(cl))
            cur_path = ln[4:].strip().split("\t", 1)[0]
            cur_lines = [ln]
        else:
            cur_lines.append(ln)
    if cur_path is not None:
        stripped = _strip_app_prefix(cur_path)
        out_chunks.append(f"diff --git a/{stripped} b/{stripped}")
        out_chunks.append(f"--- a/{stripped}")
        for cl in cur_lines:
            out_chunks.append(_normalize_diff_line(cl))
    return "\n".join(out_chunks)


def extract_patch(spec: RunSpec) -> bool:
    """Pull the agent's git diff out of the trajectory / agent.json and
    save it as ``patch.txt``.

    For mini-swe-agent: read the trajectory's tool-output stream and
    extract the LAST ``git diff`` block. This is what the agent
    produced via ``git diff -- path1 path2 > patch.txt`` (or
    ``cat patch.txt``) inside the docker container. The previous
    approach (read ``info.submission``) was broken because the
    submission text is the agent's *last assistant message* which has
    hunk-header line counts that don't match the body — ``git apply``
    rejected 29/46 of our pilot-20 patches as ``corrupt patch`` for
    this reason. The trajectory's tool outputs are verbatim from
    ``git diff``, so they are correct by construction.

    For openhands: read stdout_tail from agent.json for the patch.

    Returns True on success.
    """
    if spec.row.raw.get("source_split", {}).get("agent") == "mini-swe-agent":
        traj_path = spec.out_dir / "trajectory.json"
        if not traj_path.exists():
            return False
        try:
            traj = json.loads(traj_path.read_text())
        except Exception:
            return False

        # 1) Try the trajectory tool-output stream. This is the most
        #    reliable source — it's the verbatim ``git diff`` output.
        diff_block = _extract_last_git_diff_from_messages(traj.get("messages", []))
        if diff_block:
            (spec.out_dir / "patch.txt").write_text(diff_block)
            return True

        # 2) Fallback: info.submission (legacy, broken on real issues).
        submission = (traj.get("info") or {}).get("submission") or ""
        if submission.strip():
            rewritten = _submission_to_git_diff(submission)
            if rewritten and rewritten.strip():
                (spec.out_dir / "patch.txt").write_text(rewritten)
                return True

        # 3) Last resort: search the entire JSON blob for ``diff --git``
        #    text. Only safe if there's exactly one occurrence.
        blob = json.dumps(traj)
        if "diff --git " in blob:
            i = blob.find("diff --git ")
            end = blob.rfind("```", 0, len(blob))
            chunk = blob[i:end] if end > i else blob[i:]
            (spec.out_dir / "patch.txt").write_text(chunk)
            return True
        return False

    # openhands: the host patch was already copied to patch.txt by
    # run_one_agent (when the agent ran in the testbed cwd). If that
    # didn't happen (e.g. the agent failed), fall back to stdout_tail.
    if (spec.out_dir / "patch.txt").exists():
        # Already produced by run_one_agent; only accept it if non-empty.
        return (spec.out_dir / "patch.txt").stat().st_size > 0
    agent_log = spec.out_dir / "agent.json"
    if not agent_log.exists():
        return False
    log = json.loads(agent_log.read_text())
    out = (log.get("stdout_tail") or "") + "\n" + (log.get("stderr_tail") or "")
    if "+++ " in out or "diff --git " in out:
        i = out.find("+++ ") if out.find("+++ ") != -1 else out.find("diff --git ")
        (spec.out_dir / "patch.txt").write_text(out[i:])
        return True
    return False


def _extract_last_git_diff_from_messages(messages: list[dict]) -> str | None:
    """Pull the last ``diff --git`` block out of a mini-swe-agent trajectory.

    Walks the messages in order, finds every tool output that contains
    a ``diff --git`` line, parses out the body (between ``<output>``
    tags or starting from the ``diff --git`` line), and returns the
    *last* such body. Returns None if no diff was ever produced.
    """
    import re

    last: str | None = None
    for msg in messages:
        if msg.get("role") != "tool":
            continue
        content = msg.get("content")
        if not isinstance(content, str) or "diff --git" not in content:
            continue
        # mini-swe-agent wraps tool outputs in <output>...</output> tags.
        m_out = re.search(r"<output>\n?(.*?)\n?</output>", content, re.DOTALL)
        body = m_out.group(1) if m_out else content
        # Trim anything after the last diff hunk (e.g. shell prompt echo).
        if "diff --git" in body:
            idx = body.find("diff --git")
            body = body[idx:].rstrip() + "\n"
            # Sanity: must contain at least one hunk header
            if "@@ " in body:
                last = body
    return last


def rollout_rows(rows: list[Row], *,
                 skill_modes: list[bool],
                 model: str,
                 cost_limit: float,
                 max_rows: int | None = None,
                 skip_done: bool = True,
                 dry_build_only: bool = False,
                 cleanup_images: bool = False) -> dict[str, int]:
    """Top-level orchestration loop.

    Steps per (row, skill_mode):
        1. Resolve spec + skip if done (unless ``skip_done=False``).
        2. Build docker image (only once per row, regardless of skill_mode).
        3. If ``dry_build_only``, stop here.
        4. For each skill_mode: build prompt, invoke agent, extract patch.

    If ``cleanup_images`` is True, the row's image is removed once *all*
    skill_modes finish successfully (or the build failed). Images are
    not removed if the build was cached from a prior batch — in that
    case another batch may still need them.

    Returns a stats dict ``{built, skipped, ok, failed, error}``.
    """
    stats = {"planned": 0, "built": 0, "skipped": 0, "ok": 0, "failed": 0,
             "build_fail": 0, "agent_fail": 0, "patch_missing": 0,
             "rows_seen": 0, "rows_done": 0}

    if max_rows is not None:
        rows = rows[:max_rows]

    for r_idx, row in enumerate(rows, 1):
        specs = [spec_for_row(row, with_skill=m) for m in skill_modes]
        stats["rows_seen"] += 1

        # Skip whole row if all skill_modes already done.
        if skip_done and all(spec_is_done(s) for s in specs):
            stats["rows_done"] += 1
            stats["skipped"] += len(specs)
            print(f"[{r_idx}/{len(rows)}] {row.id}  SKIP (all done)")
            continue

        print(f"[{r_idx}/{len(rows)}] {row.id}  repo={row.repo}  base={row.base_sha[:8] if row.base_sha else '?'}")

        # Build image (once per row). Both skill modes share this
        # image, so the meta lives at the row level (not under
        # with_skill/ or without_skill/) and the tag is skill-mode-
        # agnostic.
        build_tag = specs[0].image_tag
        key = f"{specs[0].row.raw.get('source_split', {}).get('agent') or 'mini-swe-agent'}_{specs[0].row.raw.get('source_split', {}).get('train_size_requested') or '?'}"
        safe_repo = row.repo.replace("/", "__")
        image_meta_path = RUNS_ROOT / key / f"{safe_repo}__{row.id}" / "image_meta.json"
        if not image_meta_path.exists():
            ok, log = build_one_image(specs[0])
            image_meta_path.parent.mkdir(parents=True, exist_ok=True)
            image_meta = {
                "tag": build_tag,
                "built_at": _now(),
                "ok": ok,
                "log_tail": log[-3000:],
            }
            image_meta_path.write_text(json.dumps(image_meta, indent=2))
            if not ok:
                for s in specs:
                    (s.out_dir).mkdir(parents=True, exist_ok=True)
                    (s.out_dir / "_build_failed.json").write_text(
                        json.dumps({"image_tag": build_tag, "log_tail": log[-3000:]}, indent=2))
                stats["build_fail"] += 1
                print(f"  ✗ docker build failed (see image_meta.json)")
                continue
            stats["built"] += 1
            print(f"  ✓ docker build → {build_tag}")
        else:
            meta = json.loads(image_meta_path.read_text())
            if not meta.get("ok"):
                stats["build_fail"] += 1
                print(f"  ✗ prior build failed (cached) — skipping row")
                continue
            print(f"  ↻ docker build cached → {build_tag}")

        if dry_build_only:
            continue

        # Run agent for each skill_mode.
        for spec in specs:
            stats["planned"] += 1
            if skip_done and spec_is_done(spec):
                stats["skipped"] += 1
                stats["ok"] += 1
                print(f"  · {spec.out_dir.name}  SKIP (already done)")
                continue
            prompt, skill = build_prompt(spec.row, with_skill=spec.with_skill)
            print(f"  · {spec.out_dir.name}  prompt={len(prompt)}c  skill={'on' if spec.with_skill else 'off'}")
            t0 = time.time()
            try:
                run_one_agent(spec, prompt, model=model, cost_limit=cost_limit)
            except subprocess.TimeoutExpired:
                stats["agent_fail"] += 1
                (spec.out_dir / "_timeout.json").write_text(json.dumps(
                    {"wall_seconds": time.time() - t0, "ran_at": _now()}, indent=2))
                print(f"    ✗ timeout after {DEFAULT_WALL_TIMEOUT}s")
                continue
            except Exception as e:
                stats["agent_fail"] += 1
                (spec.out_dir / "_agent_error.json").write_text(json.dumps(
                    {"error": repr(e), "ran_at": _now()}, indent=2))
                print(f"    ✗ agent error: {e!r}")
                continue
            if extract_patch(spec):
                stats["ok"] += 1
                print(f"    ✓ patch extracted ({time.time()-t0:.1f}s)")
            else:
                stats["patch_missing"] += 1
                (spec.out_dir / "_no_patch.json").write_text(json.dumps(
                    {"ran_at": _now()}, indent=2))
                print(f"    ✗ no patch extracted")

        # Per-row image cleanup — only for images we *built* in this
        # call. Cached images (image_meta.json existed before this
        # call) are left in place so other batches can still reuse them.
        if cleanup_images and image_meta_path.exists() and 'image_meta' in dir():
            if image_meta.get("ok"):
                _cleanup_image(build_tag)

    return stats


def _cleanup_image(tag: str) -> None:
    """Best-effort ``docker image rm`` for one tag. Errors are logged
    but do not abort the batch — the run artifacts are on disk already."""
    try:
        subprocess.run(
            ["docker", "image", "rm", tag],
            check=False, capture_output=True, text=True, timeout=300,
        )
        print(f"  · docker image rm {tag}")
    except Exception as e:
        print(f"  · docker image rm {tag} skipped: {e!r}")


def cmd_status(rows: Iterable[Row], *, skill_modes: list[bool]) -> int:
    counts = {"done": 0, "failed": 0, "missing": 0, "build_failed": 0}
    for row in rows:
        for with_skill in skill_modes:
            spec = spec_for_row(row, with_skill=with_skill)
            if spec_is_done(spec):
                counts["done"] += 1
            elif spec_is_failed(spec):
                counts["failed"] += 1
            elif (spec.out_dir.parent / "image_meta.json").exists():
                counts["missing"] += 1
            else:
                counts["build_failed"] += 1
    print(json.dumps(counts, indent=2))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _resolve_skill_modes(arg: str) -> list[bool]:
    if arg == "all":
        return [True, False]
    if arg == "with":
        return [True]
    if arg == "without":
        return [False]
    raise ValueError(arg)


def _load_index_rows(index_path: Path, only_test: bool) -> list[Row]:
    rows = load_rows(index_path, only_test=only_test)
    if not rows:
        sys.exit(f"no rows in {index_path} (only_test={only_test})")
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Drive the agent over the verify pool.")
    sub = p.add_subparsers(dest="mode", required=True)

    def add_io(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--index", type=Path, required=True,
                        help="issue_index_*.jsonl")
        sp.add_argument("--pilot-id", type=str, default=None,
                        help="Limit to one issue id (e.g. issue-1077).")
        sp.add_argument("--skill-mode",
                        choices=["with", "without", "all"],
                        default="all",
                        help="with_skill only / without_skill only / both.")

    add_io(sub.add_parser("dry-run",
                          help="Print what would happen, no LLM/docker."))
    add_io(sub.add_parser("status",
                          help="Count done/missing/failed runs (no side effects)."))

    ro = sub.add_parser("rollout",
                        help="Build image + invoke agent (idempotent).")
    add_io(ro)
    ro.add_argument("--model", default=DEFAULT_MODEL)
    ro.add_argument("--cost-limit", type=float, default=DEFAULT_COST_LIMIT)
    ro.add_argument("--max-rows", type=int, default=None,
                    help="Limit to first N rows (for staged rollout).")
    ro.add_argument("--no-skip-done", action="store_true",
                    help="Re-run even if patch.txt exists.")
    ro.add_argument("--build-only", action="store_true",
                    help="Only build docker images, skip agent runs.")
    ro.add_argument("--cleanup-images", action="store_true",
                    help="After each row finishes both skill modes, "
                         "remove its docker image tag. Saves ~1-3 GB per "
                         "row but disables cross-batch image reuse.")

    score = sub.add_parser("score",
                           help="Apply patch + run test for prior runs.")
    add_io(score)

    prune = sub.add_parser("prune-images",
                           help="Remove every rq4-* docker image.")
    prune.add_argument("--dry-run", action="store_true",
                       help="List what would be removed, do not remove.")
    prune.add_argument("--repo", type=str, default=None,
                       help="Only remove images for this repo "
                            "(e.g. 'crewAIInc/crewAI').")
    prune.add_argument("--older-than-days", type=int, default=None,
                       help="Only remove images older than N days "
                            "(based on image_meta.json built_at).")

    args = p.parse_args()

    # prune-images does not need --index (it iterates image_meta.json
    # under the runs root directly), so handle it before that check.
    if args.mode == "prune-images":
        return cmd_prune_images(
            repo=args.repo,
            older_than_days=args.older_than_days,
            dry_run=args.dry_run,
        )

    if not args.index.exists():
        sys.exit(f"--index {args.index} does not exist")

    only_test = args.mode != "dry-run"
    rows = _load_index_rows(args.index, only_test=only_test)
    if args.pilot_id:
        rows = [r for r in rows if r.id == args.pilot_id]
        if not rows:
            sys.exit(f"--pilot-id {args.pilot_id!r} not in {args.index.name}")

    skill_modes = _resolve_skill_modes(args.skill_mode)

    if args.mode == "dry-run":
        if args.skill_mode == "all":
            return cmd_dry_run(rows)
        out = dry_run_row(rows[0], with_skill=skill_modes[0])
        print(fmt_dry(out))
        return 0

    if args.mode == "status":
        return cmd_status(rows, skill_modes=skill_modes)

    if args.mode == "rollout":
        stats = rollout_rows(
            rows, skill_modes=skill_modes,
            model=args.model, cost_limit=args.cost_limit,
            max_rows=args.max_rows,
            skip_done=not args.no_skip_done,
            dry_build_only=args.build_only,
            cleanup_images=args.cleanup_images,
        )
        print()
        print(json.dumps(stats, indent=2))
        return 0

    if args.mode == "score":
        sys.exit("score not implemented in this commit; see TODO in solve.py")

    return 0


def cmd_prune_images(*, repo: str | None,
                     older_than_days: int | None,
                     dry_run: bool) -> int:
    """Remove ``rq4-*`` docker images, optionally filtered by repo and
    age. Iterates over ``image_meta.json`` files so we know which tags
    exist on disk and when they were built, then asks the Docker CLI
    to remove them.

    Use this when one repo finishes — e.g. after a pilot — to free
    disk space before starting the next pilot. ``rollout --cleanup-images``
    does this per row; ``prune-images`` does it in bulk.
    """
    if not RUNS_ROOT.exists():
        print(f"runs root {RUNS_ROOT} does not exist; nothing to prune.")
        return 0

    cutoff_ts: float | None = None
    if older_than_days is not None:
        cutoff_ts = time.time() - older_than_days * 86400

    safe_repo_filter: str | None = None
    if repo:
        if "/" not in repo:
            print(f"--repo expects 'owner/name', got {repo!r}", file=sys.stderr)
            return 2
        safe_repo_filter = repo.replace("/", "__").lower()

    targets: list[tuple[str, float]] = []  # (tag, built_at_ts)
    for meta_path in RUNS_ROOT.glob("*/*/image_meta.json"):
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            continue
        tag = meta.get("tag")
        built_at = meta.get("built_at", "")
        if not tag:
            continue
        # Filter by repo.
        if safe_repo_filter and safe_repo_filter not in tag.lower():
            continue
        # Filter by age.
        if cutoff_ts is not None:
            try:
                from datetime import datetime
                ts = datetime.fromisoformat(built_at).timestamp()
            except Exception:
                continue
            if ts > cutoff_ts:
                continue
        targets.append((tag, ts))

    if not targets:
        print("no matching images to prune.")
        return 0

    print(f"{len(targets)} image(s) match:")
    for tag, _ in targets:
        print(f"  {tag}")

    if dry_run:
        print("(dry-run) no images removed.")
        return 0

    removed = 0
    for tag, _ in targets:
        r = subprocess.run(
            ["docker", "image", "rm", tag],
            check=False, capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0:
            removed += 1
            print(f"  ✓ removed {tag}")
        else:
            err = r.stderr.strip() or r.stdout.strip() or "(no output)"
            print(f"  ✗ {tag}: {err.splitlines()[0] if err else 'unknown'}")

    # Also prune dangling layers so the daemon reclaims the disk space.
    subprocess.run(
        ["docker", "image", "prune", "-f"],
        check=False, capture_output=True, text=True, timeout=300,
    )
    print(f"removed {removed}/{len(targets)} image(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
