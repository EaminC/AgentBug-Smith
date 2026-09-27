#!/usr/bin/env python3
"""
calculate_avg_mini_swe_cost.py
Computes token footprints and costs for mini-swe-agent trajectories
using fixed GPT-4.1-mini pricing.

Run simply:
    python calculate_avg_mini_swe_cost.py --results-dir ./mini_swe_results
"""

import argparse
import json
from pathlib import Path
import numpy as np

# ==========================================
# Fixed Rate Card for GPT-4.1-mini (per token)
# Rates: $0.40/1M uncached in, $0.10/1M cached in, $1.60/1M output
# ==========================================
RATES = {
    "uncached_in": 0.40 / 1_000_000,
    "cached_in": 0.10 / 1_000_000,
    "out": 1.60 / 1_000_000,
}


def parse_single_trajectory(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[-] Error reading {path}: {e}")
        return None

    # Instance cost if recorded in info block
    model_stats = data.get("info", {}).get("model_stats", {})
    recorded_cost = model_stats.get("instance_cost")
    api_calls = model_stats.get("api_calls", 0)

    total_prompt = 0
    total_cached = 0
    total_completion = 0
    summed_turn_costs = 0.0

    for msg in data.get("messages", []):
        extra = msg.get("extra", {})
        if not isinstance(extra, dict):
            continue

        if "cost" in extra and extra["cost"] is not None:
            summed_turn_costs += float(extra["cost"])

        response = extra.get("response", {})
        usage = response.get("usage", {})
        if usage:
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            details = usage.get("prompt_tokens_details", {}) or {}
            cached = details.get("cached_tokens", 0)

            total_prompt += p_tok
            total_cached += cached
            total_completion += c_tok

    uncached_prompt = max(0, total_prompt - total_cached)

    # Calculate exact cost using standard pricing formula
    recalculated_cost = (
        (uncached_prompt * RATES["uncached_in"])
        + (total_cached * RATES["cached_in"])
        + (total_completion * RATES["out"])
    )

    cost_to_use = recorded_cost if recorded_cost is not None else summed_turn_costs
    if cost_to_use == 0.0 and (total_prompt > 0 or total_completion > 0):
        cost_to_use = recalculated_cost

    instance_id = path.parent.name if path.name == "trajectory.json" else path.stem.replace(".traj", "")

    return {
        "instance_id": instance_id,
        "api_calls": api_calls,
        "total_prompt_tokens": total_prompt,
        "cached_prompt_tokens": total_cached,
        "uncached_prompt_tokens": uncached_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "recorded_cost_usd": cost_to_use,
        "recalculated_cost_usd": recalculated_cost,
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate average cost for mini-swe-agent with fixed GPT-4.1-mini rates.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Path to folder containing mini-swe-agent trajectory files.",
    )
    args = parser.parse_args()

    # Discover trajectory files
    traj_files = sorted(list(args.results_dir.rglob("trajectory.json")))
    if not traj_files:
        traj_files = sorted(list(args.results_dir.rglob("*.traj.json")))

    if not traj_files:
        print(f"[-] No trajectory files found in {args.results_dir}")
        return

    records = []
    for f in traj_files:
        res = parse_single_trajectory(f)
        if res:
            records.append(res)

    if not records:
        print("[-] No records extracted.")
        return

    # Print Itemized Table
    print(f"\n{'Instance / Folder':<38} | {'API Calls':<9} | {'Prompt Tok':<10} | {'Cached Tok':<10} | {'Comp Tok':<8} | {'Cost (USD)':<10}")
    print("-" * 98)

    for r in records:
        print(
            f"{r['instance_id'][:38]:<38} | "
            f"{r['api_calls']:<9} | "
            f"{r['total_prompt_tokens']:<10} | "
            f"{r['cached_prompt_tokens']:<10} | "
            f"{r['completion_tokens']:<8} | "
            f"${r['recalculated_cost_usd']:<9.4f}"
        )

    # Compute Averages
    n = len(records)
    recalc_costs = [r["recalculated_cost_usd"] for r in records]
    prompt_tokens = [r["total_prompt_tokens"] for r in records]
    cached_tokens = [r["cached_prompt_tokens"] for r in records]
    comp_tokens = [r["completion_tokens"] for r in records]
    total_tokens = [r["total_tokens"] for r in records]
    api_calls = [r["api_calls"] for r in records]

    print("=" * 98)
    print(f"Summary Statistics Across {n} Patches (GPT-4.1-mini):")
    print(f"  • Total Cost                      : ${sum(recalc_costs):.4f}")
    print(f"  • Total Tokens Processed          : {sum(total_tokens):,} (Prompt: {sum(prompt_tokens):,} | Output: {sum(comp_tokens):,})")
    print("-" * 98)
    print(f"  • Average Cost per Patch          : ${np.mean(recalc_costs):.4f} (± ${np.std(recalc_costs):.4f})")
    print(f"  • Average Total Tokens / Patch    : {np.mean(total_tokens):,.1f}")
    print(f"  • Average Prompt Tokens           : {np.mean(prompt_tokens):,.1f} (Cached: {np.mean(cached_tokens):,.1f})")
    print(f"  • Average Completion Tokens       : {np.mean(comp_tokens):,.1f}")
    print(f"  • Average API Calls / Patch       : {np.mean(api_calls):.1f}")
    print("=" * 98)

    # Save summary report JSON
    summary_path = args.results_dir / "mini_swe_cost_summary.json"
    summary_data = {
        "model": "gpt-4.1-mini",
        "pricing_per_1m": {"uncached_input": 0.40, "cached_input": 0.10, "output": 1.60},
        "num_patches": n,
        "total_cost_usd": round(sum(recalc_costs), 4),
        "avg_cost_per_patch_usd": round(float(np.mean(recalc_costs)), 4),
        "std_cost_usd": round(float(np.std(recalc_costs)), 4),
        "avg_tokens_per_patch": round(float(np.mean(total_tokens)), 1),
        "avg_prompt_tokens": round(float(np.mean(prompt_tokens)), 1),
        "avg_completion_tokens": round(float(np.mean(comp_tokens)), 1),
        "details": records,
    }
    summary_path.write_text(json.dumps(summary_data, indent=2))
    print(f"[✓] Summary saved to: {summary_path}\n")


if __name__ == "__main__":
    main()