"""
calculate_patch_test_durations.py

This script scans result folders for issue_*.json files, keeps the issues that
contain test_paths_in_patch, and sums the corresponding evaluation duration from
the sibling run.log file.

Usage:
    python tools/calculate_patch_test_durations.py
    python tools/calculate_patch_test_durations.py --results-dir results/deepseek-v3.2
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "results"
RUN_LOG_NAME = "run.log"


def iter_issue_json_files(results_dir: Path) -> Iterable[Path]:
    """Yield every issue_*.json file under the results tree."""
    yield from results_dir.rglob("issue_*.json")


def has_test_paths_in_patch(data: dict) -> bool:
    """Return True when test_paths_in_patch has a non-empty value."""

    value = data.get("test_paths_in_patch")
    if value:
        return True

    linked_prs = data.get("linked_prs") or []
    for linked_pr in linked_prs:
        if linked_pr.get("test_paths_in_patch"):
            return True

    return False


def extract_duration_seconds(run_log_path: Path) -> Optional[float]:
    """Extract the total duration in seconds from a run.log file."""
    try:
        lines = run_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        seconds_match = re.search(
            r"Total Duration:\s*.*\(([-\d.]+) seconds\)\s*$",
            line,
        )
        if seconds_match:
            return float(seconds_match.group(1))

        hms_match = re.search(r"Total Duration:\s*(\d+):(\d{2}):(\d{2})\s*$", line)
        if hms_match:
            hours = int(hms_match.group(1))
            minutes = int(hms_match.group(2))
            seconds = int(hms_match.group(3))
            return float(hours * 3600 + minutes * 60 + seconds)

    return None


def format_seconds(total_seconds: float) -> str:
    seconds = int(round(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h {minutes}m {secs}s"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate total and average duration for issue JSON files that have test_paths_in_patch."
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help=f"Root results directory to scan (default: {DEFAULT_RESULTS_DIR})",
    )
    args = parser.parse_args()

    results_dir = args.results_dir.resolve()
    if not results_dir.exists():
        print(f"Error: results directory not found: {results_dir}")
        return

    total_duration = 0.0
    matched_issues = 0
    skipped_without_duration = 0

    for issue_json_path in iter_issue_json_files(results_dir):
        try:
            data = json.loads(issue_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Warning: could not read {issue_json_path}: {exc}")
            continue

        if not has_test_paths_in_patch(data):
            continue

        run_log_path = issue_json_path.with_name(RUN_LOG_NAME)
        duration_seconds = extract_duration_seconds(run_log_path)
        if duration_seconds is None:
            skipped_without_duration += 1
            continue

        matched_issues += 1
        total_duration += duration_seconds

    if matched_issues == 0:
        print("No matching issue JSON files with readable durations were found.")
        return

    average_duration = total_duration / matched_issues

    print(f"Matched issues: {matched_issues}")
    print(f"Skipped issues without duration: {skipped_without_duration}")
    print(f"Total duration: {total_duration:.2f} seconds ({format_seconds(total_duration)})")
    print(f"Average duration: {average_duration:.2f} seconds ({format_seconds(average_duration)})")


if __name__ == "__main__":
    main()