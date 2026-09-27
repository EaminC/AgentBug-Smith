#!/usr/bin/env python3
"""
After the end-to-end pipeline runs, report the remaining issue/instance count at each step.
Paths can be overridden via arguments; defaults match the timestamped run layout.
"""

import argparse
import json
from pathlib import Path
from typing import Optional

# Default paths (relative to swe-factory repo root)
DEFAULTS = {
    "issue_pr_map": "baseline/issue_pr_map.json",
    "prs": "data/my_instances/prs.jsonl",
    "instances": "data/my_instances/instances.jsonl",
    "instances_versions": "data/my_instances/instances_versions.jsonl",
    "results": "output/gpt-4.1-mini/mypy/results/results.json",
    "predictions": "output/gpt-4.1-mini/mypy/predictions.json",
    "fail2pass_report": "reports/gold.mypy_fail2pass_check.json",
}


def load_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def count_jsonl(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                n += 1
    return n


def count_json_array(path: Path) -> Optional[int]:
    data = load_json(path)
    if data is None:
        return None
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        # predictions.json: { instance_id: pred, ... }
        return len(data)
    return None


def main(root: Path, paths: dict) -> None:
    root = root.resolve()
    steps = [
        ("1. issue_pr_map (input)", paths["issue_pr_map"], "json_array"),
        ("2. prs.jsonl", paths["prs"], "jsonl"),
        ("3. instances.jsonl", paths["instances"], "jsonl"),
        ("4. instances_versions.jsonl", paths["instances_versions"], "jsonl"),
        ("5. results.json (SWE-Builder)", paths["results"], "json_array"),
        ("6. predictions.json", paths["predictions"], "json_array"),
        ("7. Fail2Pass report", paths["fail2pass_report"], "fail2pass"),
    ]
    max_label = max(len(s[0]) for s in steps)
    print("Step".ljust(max_label + 2) + "Path".ljust(50) + "Count")
    print("-" * (max_label + 2 + 50 + 12))

    for label, rel_path, kind in steps:
        full = root / rel_path
        if kind == "jsonl":
            n = count_jsonl(full)
        elif kind == "json_array":
            n = count_json_array(full)
        elif kind == "fail2pass":
            data = load_json(full)
            if data is None:
                n_str = "N/A (file missing)"
            else:
                total = data.get("total", 0)
                cats = data.get("categories", {})
                fail2pass = len(cats.get("fail2pass", []))
                n_str = f"{total} (fail2pass: {fail2pass})"
            print(f"{label.ljust(max_label + 2)}{str(rel_path).ljust(50)}{n_str}")
            continue
        else:
            n = None

        if n is None:
            n_str = "N/A (file missing)"
        else:
            n_str = str(n)
        print(f"{label.ljust(max_label + 2)}{str(rel_path).ljust(50)}{n_str}")

    print("-" * (max_label + 2 + 50 + 12))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="swe-factory repo root (default: parent of script dir)",
    )
    parser.add_argument("--issue_pr_map", type=str, default=DEFAULTS["issue_pr_map"], help="issue_pr_map path")
    parser.add_argument("--prs", type=str, default=DEFAULTS["prs"], help="prs.jsonl path")
    parser.add_argument("--instances", type=str, default=DEFAULTS["instances"], help="instances.jsonl path")
    parser.add_argument("--instances_versions", type=str, default=DEFAULTS["instances_versions"], help="instances_versions.jsonl path")
    parser.add_argument("--results", type=str, default=DEFAULTS["results"], help="results.json path")
    parser.add_argument("--predictions", type=str, default=DEFAULTS["predictions"], help="predictions.json path")
    parser.add_argument("--fail2pass_report", type=str, default=DEFAULTS["fail2pass_report"], help="Fail2Pass report JSON path")
    args = parser.parse_args()

    paths = {
        "issue_pr_map": args.issue_pr_map,
        "prs": args.prs,
        "instances": args.instances,
        "instances_versions": args.instances_versions,
        "results": args.results,
        "predictions": args.predictions,
        "fail2pass_report": args.fail2pass_report,
    }
    main(args.root, paths)
