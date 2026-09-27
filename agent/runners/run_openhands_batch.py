#!/usr/bin/env python3
"""
Batch Patch Generator using OpenHands SDK v1.34.0 (CodeActAgent).
Registers workspace tools (terminal, file_editor), iterates over issue
artifacts, executes the agent, and writes `generated_patch.diff`, `cost.json`,
and `openhands_run.log`.

Run the script:
python exp/run_openhands_batch.py --artifacts-dir /root/OpenHands/artifacts --output-dir /root/OpenHands/patches --model openai/tuzi-gpt-4.1-mini/deepseek-v3.2 --max-iterations 60
"""

import os
import sys
import json
import shutil
import asyncio
import warnings
import subprocess
import argparse
from pathlib import Path

# Suppress ASCII banner
os.environ["OPENHANDS_SUPPRESS_BANNER"] = "1"

# Suppress unmapped model cost calculation warnings from OpenHands telemetry
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    message=r".*Cost calculation failed: This model isn't mapped yet.*",
)

# Register custom model identifiers into LiteLLM's cost engine
try:
    import litellm

    litellm_rates = {
        # Exact slug queried by OpenHands / LiteLLM telemetry
        "tuzi-gpt-4.1-mini/deepseek-v3.2": {
            "input_cost_per_token": 0.28 / 1_000_000,
            "output_cost_per_token": 0.42 / 1_000_000,
            "cache_read_input_token_cost": 0.028 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "openai/tuzi-gpt-4.1-mini/deepseek-v3.2": {
            "input_cost_per_token": 0.28 / 1_000_000,
            "output_cost_per_token": 0.42 / 1_000_000,
            "cache_read_input_token_cost": 0.028 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "tuzi-gpt-4.1-mini/kimi-k2.5": {
            "input_cost_per_token": 0.60 / 1_000_000,
            "output_cost_per_token": 2.50 / 1_000_000,
            "cache_read_input_token_cost": 0.10 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "openai/tuzi-gpt-4.1-mini/kimi-k2.5": {
            "input_cost_per_token": 0.60 / 1_000_000,
            "output_cost_per_token": 2.50 / 1_000_000,
            "cache_read_input_token_cost": 0.10 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "tuzi-gpt-4.1-mini/gpt-4.1-mini": {
            "input_cost_per_token": 0.40 / 1_000_000,
            "output_cost_per_token": 1.60 / 1_000_000,
            "cache_read_input_token_cost": 0.10 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "openai/tuzi-gpt-4.1-mini/gpt-4.1-mini": {
            "input_cost_per_token": 0.40 / 1_000_000,
            "output_cost_per_token": 1.60 / 1_000_000,
            "cache_read_input_token_cost": 0.10 / 1_000_000,
            "litellm_provider": "openai",
            "mode": "chat",
        },
    }
    litellm.register_model(litellm_rates)
except Exception:
    pass

from openhands.sdk import (
    LLM,
    Agent,
    LocalWorkspace,
    LocalConversation,
    Message,
    TextContent,
)
from openhands.sdk.tool.spec import Tool
from openhands.tools import register_default_tools

# Register tools once globally
register_default_tools()

# Rate cards ($ / token)
MODEL_RATE_CARDS = {
    "gpt-4.1-mini": {
        "uncached_in": 0.40 / 1_000_000,
        "cached_in": 0.10 / 1_000_000,
        "out": 1.60 / 1_000_000,
    },
    "deepseek-v3.2": {
        "uncached_in": 0.28 / 1_000_000,
        "cached_in": 0.028 / 1_000_000,
        "out": 0.42 / 1_000_000,
    },
    "kimi-k2.5": {
        "uncached_in": 0.60 / 1_000_000,
        "cached_in": 0.10 / 1_000_000,
        "out": 2.50 / 1_000_000,
    },
}


def get_model_rates(model_name: str) -> tuple[str, dict]:
    """Matches the model string to one of the 3 supported rate cards."""
    name = model_name.lower()
    if "kimi" in name or "k2.5" in name:
        return "kimi-k2.5", MODEL_RATE_CARDS["kimi-k2.5"]
    elif "deepseek" in name or "v3.2" in name:
        return "deepseek-v3.2", MODEL_RATE_CARDS["deepseek-v3.2"]
    elif "gpt-4.1-mini" in name or "4.1-mini" in name:
        return "gpt-4.1-mini", MODEL_RATE_CARDS["gpt-4.1-mini"]
    else:
        # Default fallback to gpt-4.1-mini
        print(f"[!] Warning: Model '{model_name}' unrecognized. Defaulting to 'gpt-4.1-mini' rate card.")
        return "gpt-4.1-mini", MODEL_RATE_CARDS["gpt-4.1-mini"]


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        capture_output=True,
    )


def extract_val(obj, *keys) -> int:
    """Safely extracts integer token counts from either dictionaries or objects."""
    if not obj:
        return 0
    for key in keys:
        if isinstance(obj, dict):
            val = obj.get(key)
        else:
            val = getattr(obj, key, None)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return 0


async def solve_single_issue(
    artifact_dir: Path,
    output_dir: Path,
    repos_cache_dir: Path,
    model_name: str,
    api_key: str,
    base_url: str | None = None,
    max_iterations: int = 30,
):
    issue_folder = artifact_dir.name
    print("\n" + "=" * 60)
    print(f"[*] Processing Artifact: {issue_folder}")
    print("=" * 60)

    # Parse Issue Metadata
    json_files = sorted(list(artifact_dir.glob("issue_*.json"))) or sorted(list(artifact_dir.glob("*.json")))
    if not json_files:
        print(f"[-] No issue JSON found in {artifact_dir}. Skipping.")
        return

    with open(json_files[0], "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    issue_num = str(issue_data.get("number") or issue_folder)
    linked_prs = issue_data.get("linked_prs", [])
    base_sha = linked_prs[0].get("base_sha") if linked_prs else issue_data.get("base_sha")
    raw_url = issue_data.get("url", "")
    repo_url = (raw_url.split("/issues/")[0] + ".git") if "/issues/" in raw_url else raw_url

    title = issue_data.get("title", "")
    body = issue_data.get("body", "")
    problem_statement = f"Issue Title: {title}\n\nDescription:\n{body}"

    # Setup directories
    patch_target_dir = output_dir / f"result_{issue_folder}"
    patch_target_dir.mkdir(parents=True, exist_ok=True)
    patch_file_path = patch_target_dir / "generated_patch.diff"
    log_file_path = patch_target_dir / "openhands_run.log"
    cost_file_path = patch_target_dir / "cost.json"

    workspace_path = repos_cache_dir / f"openhands_ws_{issue_num}"
    if workspace_path.exists():
        shutil.rmtree(workspace_path)

    try:
        # Clone and checkout base buggy commit
        print(f"[*] Cloning {repo_url} at base commit {base_sha}...")
        clone_res = run_cmd(["git", "clone", repo_url, str(workspace_path)])
        if clone_res.returncode != 0:
            print(f"[-] Git clone failed: {clone_res.stderr}")
            return

        if base_sha:
            run_cmd(["git", "checkout", base_sha], cwd=workspace_path)

        # Instantiate LLM & Agent without the browser tool
        llm_kwargs = {"model": model_name, "api_key": api_key}
        if base_url:
            llm_kwargs["base_url"] = base_url

        llm = LLM(**llm_kwargs)

        coding_tools = [
            Tool(name="terminal", params={}),
            Tool(name="file_editor", params={}),
            Tool(name="task_tracker", params={}),
        ]

        agent = Agent(llm=llm, tools=coding_tools)
        workspace = LocalWorkspace(working_dir=workspace_path.resolve())

        # Formulate Prompt & Launch Conversation Loop
        instruction = (
            f"You are an expert autonomous software engineer tasked with fixing a bug in this repository.\n\n"
            f"{problem_statement}\n\n"
            f"Guidelines:\n"
            f"1. Quickly locate the relevant files and bug root cause using terminal/file_editor.\n"
            f"2. Apply the necessary minimal code fixes using file_editor.\n"
            f"3. Run tests or verify changes if possible.\n"
            f"4. Call the finish tool as soon as the issue is resolved. Do NOT run git commit."
        )

        print(f"[*] Launching OpenHands LocalConversation (Max Iterations: {max_iterations})...")
        conversation = LocalConversation(
            agent=agent,
            workspace=workspace,
            max_iteration_per_run=max_iterations,
            visualizer=None,
        )

        # Send instruction and execute conversation
        msg = Message(role="user", content=[TextContent(text=instruction)])
        conversation.send_message(msg)
        await conversation.arun()

        # Extract Metrics & Save cost.json
        matched_model_key, rates = get_model_rates(model_name)
        metrics = None
        if hasattr(conversation, "conversation_stats") and conversation.conversation_stats:
            try:
                metrics = conversation.conversation_stats.get_combined_metrics()
            except Exception:
                metrics = None
        elif hasattr(llm, "metrics") and llm.metrics:
            metrics = llm.metrics

        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0

        # Aggregate usage object
        if metrics and getattr(metrics, "accumulated_token_usage", None):
            u = metrics.accumulated_token_usage
            input_tokens = extract_val(u, "prompt_tokens", "input_tokens")
            output_tokens = extract_val(u, "completion_tokens", "output_tokens")
            cached_tokens = extract_val(u, "cache_read_tokens", "cache_read_input_tokens")

        # Fallback to iterating state events
        if input_tokens == 0 and hasattr(conversation, "state") and hasattr(conversation.state, "events"):
            for event in conversation.state.events:
                usage = (
                    getattr(event, "usage", None)
                    or getattr(getattr(event, "response", None), "usage", None)
                )
                if usage:
                    input_tokens += extract_val(usage, "prompt_tokens", "input_tokens")
                    output_tokens += extract_val(usage, "completion_tokens", "output_tokens")

                    # Handle cached tokens both flat and inside prompt_tokens_details
                    cached = extract_val(usage, "cache_read_tokens", "cache_read_input_tokens")
                    if not cached:
                        details = (
                            usage.get("prompt_tokens_details")
                            if isinstance(usage, dict)
                            else getattr(usage, "prompt_tokens_details", None)
                        )
                        cached = extract_val(details, "cached_tokens")
                    cached_tokens += cached

        uncached_in = max(0, input_tokens - cached_tokens)
        cost_usd = (
            (uncached_in * rates["uncached_in"])
            + (cached_tokens * rates["cached_in"])
            + (output_tokens * rates["out"])
        )

        cost_data = {
            "instance_id": issue_folder,
            "model": matched_model_key,
            "raw_model_name": model_name,
            "input_tokens": input_tokens,
            "cached_tokens": cached_tokens,
            "uncached_tokens": uncached_in,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost_usd, 6),
        }
        cost_file_path.write_text(json.dumps(cost_data, indent=2), encoding="utf-8")
        print(f"[✓] Saved cost.json ({matched_model_key}): ${cost_usd:.4f} ({input_tokens} in [cached: {cached_tokens}], {output_tokens} out)")

        # Extract Detailed Execution Log from State Events
        log_lines = []
        if hasattr(conversation, "state") and hasattr(conversation.state, "events"):
            for event in conversation.state.events:
                log_lines.append(f"[{event.__class__.__name__}]\n{event}\n")
        else:
            log_lines.append(str(conversation))
        log_file_path.write_text("\n".join(log_lines), encoding="utf-8")

        # Extract Git Diff (including newly created files)
        run_cmd(["git", "add", "-A", "--intent-to-add"], cwd=workspace_path)
        diff_res = run_cmd(["git", "diff"], cwd=workspace_path)
        patch_text = diff_res.stdout

        if patch_text.strip():
            patch_file_path.write_text(patch_text, encoding="utf-8")
            print(f"[✓] Generated patch saved: {patch_file_path}")
        else:
            print("[-] Finished with empty diff (no code modifications made).")

    except Exception as e:
        print(f"[-] Execution error on {issue_folder}: {e}")
        log_file_path.write_text(f"Error: {str(e)}", encoding="utf-8")
    finally:
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)


async def main_async():
    parser = argparse.ArgumentParser(description="Batch generate SWE patches using OpenHands SDK v1.34.0.")
    parser.add_argument("--artifacts-dir", type=Path, required=True, help="Directory containing issue artifact folders.")
    parser.add_argument("--output-dir", type=Path, default=Path("./openhands_patches"), help="Output directory for diffs.")
    parser.add_argument("--repos-cache", type=Path, default=Path("./.openhands_cache"), help="Temporary workspace cache.")
    parser.add_argument("--model", type=str, default=os.getenv("LLM_MODEL", "openai/tuzi-gpt-4.1-mini/deepseek-v3.2"))
    parser.add_argument("--max-iterations", type=int, default=30, help="Max turn iterations per issue.")
    args = parser.parse_args()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", None)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.repos_cache.mkdir(parents=True, exist_ok=True)

    artifacts = sorted([p for p in args.artifacts_dir.iterdir() if p.is_dir() and not p.name.startswith(".")])
    print(f"Found {len(artifacts)} issues to process.")

    for art in artifacts:
        await solve_single_issue(
            artifact_dir=art,
            output_dir=args.output_dir,
            repos_cache_dir=args.repos_cache,
            model_name=args.model,
            api_key=api_key,
            base_url=base_url,
            max_iterations=args.max_iterations,
        )

    if args.repos_cache.exists():
        shutil.rmtree(args.repos_cache, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main_async())