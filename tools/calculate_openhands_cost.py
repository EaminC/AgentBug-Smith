#!/usr/bin/env python3
"""
calculate_avg_openhands_cost.py
Scans OpenHands run directories for cost.json or openhands_run.log,
applies fixed GPT-4.1-mini rates, and outputs summary statistics.

How to run:python /root/AgentBug-Smith/tools/calculate_avg_openhands_cost.py \
  --results-dir /root/OpenHands/patches
"""

import argparse
import json
import re
import statistics
from pathlib import Path

# Rates for GPT-4.1-mini: $0.40/1M uncached in, $0.10/1M cached in, $1.60/1M output
RATES = {
    "uncached_in": 0.40 / 1_000_000,
    "cached_in": 0.10 / 1_000_000,
    "out": 1.60 / 1_000_000,
}


def check_has_patch(result_dir: Path) -> bool:
    """Checks for non-empty diff/patch files containing actual code changes."""
    patch_candidates = [
        result_dir / "generated_patch.diff",
        result_dir / "generated_patch.patch",
    ]
    patch_candidates.extend(result_dir.glob("*.diff"))
    patch_candidates.extend(result_dir.glob("*.patch"))

    for pf in patch_candidates:
        if pf.is_file() and pf.stat().st_size > 0:
            lines = [l.strip() for l in pf.read_text(errors="ignore").splitlines() if l.strip()]
            if any(l.startswith("+") or l.startswith("-") for l in lines):
                return True
    return False


def parse_openhands_instance(result_dir: Path) -> dict | None:
    instance_id = result_dir.name.replace("result_", "")
    has_patch = check_has_patch(result_dir)

    input_tokens = 0
    cached_tokens = 0
    output_tokens = 0

    # Check for cost.json or stats.json
    cost_file = result_dir / "cost.json"
    stats_file = result_dir / "stats.json"
    target_json = cost_file if cost_file.exists() else (stats_file if stats_file.exists() else None)

    if target_json:
        try:
            data = json.loads(target_json.read_text(encoding="utf-8"))
            input_tokens = data.get("input_tokens") or data.get("prompt_tokens") or 0
            cached_tokens = data.get("cached_tokens") or data.get("cache_read_tokens") or 0
            output_tokens = data.get("output_tokens") or data.get("completion_tokens") or 0
        except Exception:
            pass

    # Fallback: Parse openhands_run.log
    log_file = result_dir / "openhands_run.log"
    if input_tokens == 0 and log_file.exists():
        text = log_file.read_text(errors="ignore")
        p_matches = re.findall(r"['\"]?(?:prompt_tokens|input_tokens)['\"]?:\s*(\d+)", text)
        c_matches = re.findall(r"['\"]?(?:completion_tokens|output_tokens)['\"]?:\s*(\d+)", text)
        cache_matches = re.findall(r"['\"]?(?:cache_read_tokens|cached_tokens)['\"]?:\s*(\d+)", text)

        if p_matches:
            input_tokens = sum(map(int, p_matches))
            output_tokens = sum(map(int, c_matches))
            cached_tokens = sum(map(int, cache_matches)) if cache_matches else 0

    if input_tokens == 0 and output_tokens == 0:
        return None

    uncached_in = max(0, input_tokens - cached_tokens)
    cost = (
        (uncached_in * RATES["uncached_in"])
        + (cached_tokens * RATES["cached_in"])
        + (output_tokens * RATES["out"])
    )

    return {
        "instance_id": instance_id,
        "has_patch": has_patch,
        "input_tokens": input_tokens,
        "cached_tokens": cached_tokens,
        "uncached_tokens": uncached_in,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": round(cost, 6),
    }


def compute_metrics(records: list[dict]) -> dict:
    if not records:
        return {
            "count": 0,
            "total_cost": 0.0,
            "avg_cost": 0.0,
            "std_cost": 0.0,
            "avg_tokens": 0.0,
            "avg_input_tokens": 0.0,
            "avg_cached_tokens": 0.0,
            "avg_output_tokens": 0.0,
        }

    n = len(records)
    costs = [r["cost_usd"] for r in records]
    inputs = [r["input_tokens"] for r in records]
    cached = [r["cached_tokens"] for r in records]
    outputs = [r["output_tokens"] for r in records]
    totals = [r["total_tokens"] for r in records]

    return {
        "count": n,
        "total_cost": sum(costs),
        "avg_cost": statistics.mean(costs),
        "std_cost": statistics.stdev(costs) if n > 1 else 0.0,
        "avg_tokens": statistics.mean(totals),
        "avg_input_tokens": statistics.mean(inputs),
        "avg_cached_tokens": statistics.mean(cached),
        "avg_output_tokens": statistics.mean(outputs),
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate average cost for OpenHands.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        required=True,
        help="Path to directory containing OpenHands result_* folders.",
    )
    args = parser.parse_args()

    subdirs = sorted([d for d in args.results_dir.iterdir() if d.is_dir() and d.name.startswith("result_")])
    if not subdirs:
        subdirs = [args.results_dir]

    records = []
    for d in subdirs:
        res = parse_openhands_instance(d)
        if res:
            records.append(res)

    if not records:
        print(f"[-] No valid OpenHands runs found in {args.results_dir}")
        return

    records.sort(key=lambda x: x["instance_id"])

    print(f"\n{'Instance ID':<38} | {'Patch?':<6} | {'Input Tok':<10} | {'Cached':<8} | {'Output':<8} | {'Cost (USD)':<10}")
    print("-" * 92)

    for r in records:
        patch_flag = "YES" if r["has_patch"] else "NO"
        print(
            f"{r['instance_id'][:38]:<38} | "
            f"{patch_flag:<6} | "
            f"{r['input_tokens']:<10} | "
            f"{r['cached_tokens']:<8} | "
            f"{r['output_tokens']:<8} | "
            f"${r['cost_usd']:<9.4f}"
        )

    all_stats = compute_metrics(records)
    patch_records = [r for r in records if r["has_patch"]]
    patch_stats = compute_metrics(patch_records)
    no_patch_count = len(records) - len(patch_records)

    print("=" * 92)
    print("1. Overall (All Attempted OpenHands Tasks):")
    print(f"  • Total Issues Attempted          : {all_stats['count']}")
    print(f"  • Patches Produced                : {patch_stats['count']} (Empty/Failed: {no_patch_count})")
    print(f"  • Total Cost                      : ${all_stats['total_cost']:.4f}")
    print(f"  • Average Cost per Task           : ${all_stats['avg_cost']:.4f} (± ${all_stats['std_cost']:.4f})")
    print(f"  • Average Total Tokens / Task     : {all_stats['avg_tokens']:,.1f}")
    print(f"  • Average Input / Cached / Output : {all_stats['avg_input_tokens']:,.1f} / {all_stats['avg_cached_tokens']:,.1f} / {all_stats['avg_output_tokens']:,.1f}")

    print("-" * 92)
    print("2. Conditional (Patch-Producing Only):")
    print(f"  • Average Cost per Produced Patch : ${patch_stats['avg_cost']:.4f} (± ${patch_stats['std_cost']:.4f})")
    print(f"  • Average Total Tokens / Patch    : {patch_stats['avg_tokens']:,.1f}")
    print("=" * 92)

    summary_file = args.results_dir / "openhands_cost_summary.json"
    summary_data = {
        "model": "gpt-4.1-mini",
        "pricing_per_1m": {"uncached_input": 0.40, "cached_input": 0.10, "output": 1.60},
        "all_attempted": all_stats,
        "patch_producing_only": patch_stats,
        "details": records,
    }
    summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    print(f"[✓] Summary saved to: {summary_file}\n")


if __name__ == "__main__":
    main()