#!/usr/bin/env python3
"""_openhands_sdk_driver.py — OpenHands SDK runner for solve.py.

This script is invoked by ``utils/verify/solve.py:_run_openhands_sdk``
as a subprocess. It runs the OpenHands SDK (CodeActAgent) against
a local workspace, captures the conversation trajectory, and
extracts the patch via ``git diff`` (NOT via the agent's self-reported
diff, which is buggy).

Pattern follows alfin06's ``run_openhands_batch.py`` line 216-254:
  * ``register_default_tools()`` once at module import.
  * Build an ``Agent`` with explicit tool list (terminal, file_editor,
    task_tracker). No browser tool.
  * Use ``LocalWorkspace`` rooted at the upstream repo clone.
  * Use ``LocalConversation(max_iteration_per_run=60, visualizer=None)``.
  * After: ``git add -A --intent-to-add && git diff`` for the patch.

Usage (called from solve.py):
    python _openhands_sdk_driver.py \
        --workspace <repo_dir> \
        --model openai/<model_slug> \
        --max-iterations 60 \
        --prompt "..." \
        --out-dir <spec_out_dir> \
        --cost-limit 3.0
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

# Reduce noise from the SDK / LiteLLM on missing model rate cards.
os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*Cost calculation failed.*",
)


def _run_git_diff(workspace: Path) -> str:
    """Run ``git add -A --intent-to-add && git diff`` in ``workspace``.

    Excludes ``env.dockerfile`` and any ``tests/agentsmith_*`` files
    — those are build artifacts added by ``build_one_image`` before
    the agent runs, not edits the agent made. Also excludes common
    scratch / reproduction files agents create during debugging.
    """
    try:
        subprocess.run(
            ["git", "add", "-A", "--intent-to-add"],
            cwd=str(workspace), check=False,
            capture_output=True, text=True,
        )
    except Exception:
        pass
    proc = subprocess.run(
        ["git", "diff",
         "--", ".",
         ":!env.dockerfile",
         ":!tests/agentsmith_*",
         ":!*.db", ":!*.sqlite", ":!*.sqlite3",
         ":!patch.txt",
         ":!*.log",
         ":!test_runs",
         ":!.config",
         # Common scratch/repro files agents create
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
        cwd=str(workspace),
        check=False, capture_output=True, text=True,
    )
    return proc.stdout


async def _run_agent(
    workspace: Path, model: str, max_iterations: int,
    prompt: str, api_key: str, base_url: str | None,
    cost_limit: float,
) -> tuple[int, str, str]:
    """Run the OpenHands SDK conversation and return
    ``(exit_code, trajectory_text, log_text)``.

    ``exit_code`` follows subprocess conventions (0 = OK).
    """
    from openhands.sdk import (
        LLM, Agent, LocalWorkspace, LocalConversation,
        Message, TextContent,
    )
    from openhands.sdk.tool.spec import Tool
    from openhands.tools import register_default_tools

    register_default_tools()

    llm_kwargs: dict = {"model": model, "api_key": api_key}
    if base_url:
        llm_kwargs["base_url"] = base_url
    llm = LLM(**llm_kwargs)

    coding_tools = [
        Tool(name="terminal", params={}),
        Tool(name="file_editor", params={}),
        Tool(name="task_tracker", params={}),
    ]
    agent = Agent(llm=llm, tools=coding_tools)
    workspace_obj = LocalWorkspace(working_dir=str(workspace.resolve()))

    instruction = (
        "You are an expert autonomous software engineer tasked with "
        "fixing a bug in this repository.\n\n"
        f"{prompt}\n\n"
        "Guidelines:\n"
        "1. Quickly locate the relevant files and bug root cause using "
        "terminal / file_editor.\n"
        "2. Apply the necessary minimal code fixes using file_editor.\n"
        "3. Run tests or verify changes if possible.\n"
        "4. When the issue is resolved, finish — do NOT run git commit.\n"
    )

    conversation = LocalConversation(
        agent=agent,
        workspace=workspace_obj,
        max_iteration_per_run=max_iterations,
        visualizer=None,
    )

    msg = Message(role="user", content=[TextContent(text=instruction)])
    conversation.send_message(msg)
    try:
        await conversation.arun()
    except Exception as e:
        return 1, "", f"SDK conversation raised: {e!r}"

    # Extract trajectory + log.
    traj_text = ""
    log_text = ""
    state = getattr(conversation, "state", None)
    if state is not None and hasattr(state, "events"):
        # Full event log → trajectory.json (we only keep the summary
        # structure; agent.json has stdout/stderr already).
        events = list(state.events)
        traj_text = json.dumps(
            [getattr(e, "model_dump", lambda: str(e))() for e in events],
            indent=2, default=str,
        )
        log_text = "\n".join(
            f"[{e.__class__.__name__}]\n{e}" for e in events
        )

    # Extract usage metrics (best effort).
    try:
        stats = getattr(conversation, "conversation_stats", None)
        if stats is not None:
            metrics = stats.get_combined_metrics()
            log_text += "\n\n[metrics]\n" + json.dumps(
                getattr(metrics, "accumulated_token_usage", {}),
                default=str, indent=2,
            )
    except Exception:
        pass

    # Check the cost limit (best-effort; the SDK doesn't enforce it natively).
    # We rely on max_iterations to keep cost bounded.
    return 0, traj_text, log_text


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--model", required=True)
    p.add_argument("--max-iterations", type=int, default=60)
    p.add_argument("--prompt", required=True)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--cost-limit", type=float, default=3.0)
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    workspace: Path = args.workspace
    if not workspace.exists():
        print(f"FATAL: workspace does not exist: {workspace}", file=sys.stderr)
        return 2

    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")

    started = time.time()
    exit_code, traj_text, log_text = asyncio.run(_run_agent(
        workspace=workspace,
        model=args.model,
        max_iterations=args.max_iterations,
        prompt=args.prompt,
        api_key=api_key,
        base_url=base_url,
        cost_limit=args.cost_limit,
    ))
    elapsed = time.time() - started

    # Always extract the patch — even on partial success — so we can
    # score whatever the agent produced.
    patch_text = _run_git_diff(workspace)
    (args.out_dir / "patch.txt").write_text(patch_text, encoding="utf-8")
    (args.out_dir / "trajectory.json").write_text(traj_text or "{}", encoding="utf-8")
    (args.out_dir / "openhands_log.txt").write_text(log_text, encoding="utf-8")

    print(f"SDK run finished: exit={exit_code}, patch_chars={len(patch_text)}, "
          f"elapsed={elapsed:.1f}s", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
