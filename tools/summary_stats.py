"""
summary_stats.py
----------------

This script recursively searches for all run.log files in the result directory, extracts the final cost and total duration from each file (using the patterns 'cost: $<amount>' and 'Total Duration: ... (<seconds> seconds)'), and outputs the total and average duration and cost across all valid logs.

Usage:
    python tools/summary_stats.py

Requirements:
- Each run.log must contain both a cost and a total duration line at the end to be counted.
- If a run.log is missing either value, it is skipped.
- Duration is reported in seconds and as hours:minutes:seconds.
- Cost is reported in dollars.
"""
import os
import json

RESULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'result'))
RUN_LOG_FILENAME = 'run.log'

def find_summary_files(root_dir):
    """
    Recursively find all run.log files under the given root directory.
    Returns a list of file paths.
    """
    runlog_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if RUN_LOG_FILENAME in filenames:
            runlog_files.append(os.path.join(dirpath, RUN_LOG_FILENAME))
    return runlog_files

import re
def extract_metrics(runlog_file):
    """
    Extract the final total duration (in seconds) and cost (in dollars) from a run.log file.
    Returns (duration, cost) as floats if both are found, otherwise (None, None).
    """
    duration = None
    cost = None
    total_tokens = 0
    try:
        with open(runlog_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Extract all total_tokens occurrences
        for line in lines:
            token_match = re.search(r'total_tokens\s*[:=]?\s*([\d,]+)', line, re.IGNORECASE)
            if token_match:
                token_str = token_match.group(1).replace(',', '')
                if token_str.isdigit():
                    total_tokens += int(token_str)
        for line in reversed(lines):
            if duration is None:
                dur_match = re.search(r'Total Duration: [^\(]*\(([-\d.]+) seconds\)', line)
                if dur_match:
                    duration = float(dur_match.group(1))
            if cost is None:
                cost_match = re.search(r'cost:\s*\$([\d.]+)', line, re.IGNORECASE)
                if cost_match:
                    cost = float(cost_match.group(1))
            if duration is not None and cost is not None:
                break
        # Always return three values
        return duration, cost, total_tokens
    except Exception as e:
        print(f"Error reading {runlog_file}: {e}")
        return None, None, 0

# Count total built instances in result/f2f, result/f2p, result/p2p
def count_subfolders(path):
    try:
        return len([name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))])
    except Exception:
        return 0

def format_seconds(seconds):
        """Convert seconds to a string in Hh Mm Ss format."""
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}h {m}m {s}s"

def main():
    """
    Main entry point. Aggregates and prints total and average duration and cost from all valid run.log files.
    """
    runlog_files = find_summary_files(RESULT_DIR)
    total_files_found = len(runlog_files)
    total_duration = 0
    total_cost = 0
    total_tokens = 0
    valid_count = 0
    durations = []  # List of (duration, file)
    costs = []      # List of (cost, file)
    for file in runlog_files:
        duration, cost, tokens = extract_metrics(file)
        total_tokens += tokens
        if duration is not None and cost is not None:
            total_duration += duration
            total_cost += cost
            valid_count += 1
            durations.append((duration, file))
            costs.append((cost, file))
    if valid_count == 0:
        print("No valid run.log files found.")
        print(f"Total run.log files found: {total_files_found}")
        return
    avg_duration = total_duration / valid_count
    avg_cost = total_cost / valid_count

    # Find longest/shortest duration
    longest_duration, longest_file = max(durations, key=lambda x: x[0])
    shortest_duration, shortest_file = min(durations, key=lambda x: x[0])
    # Find most/least expensive cost
    most_expensive_cost, most_expensive_file = max(costs, key=lambda x: x[0])
    cheapest_cost, cheapest_file = min(costs, key=lambda x: x[0])

    def extract_issue_number(filepath):
        # Try to find 'issue_{number}' in the path
        match = re.search(r'issue_(\d+)', filepath)
        return match.group(0) if match else os.path.basename(os.path.dirname(filepath))

    f2f_count = count_subfolders(os.path.join(RESULT_DIR, 'f2f'))
    f2p_count = count_subfolders(os.path.join(RESULT_DIR, 'f2p'))
    p2p_count = count_subfolders(os.path.join(RESULT_DIR, 'p2p'))
    total_built_instances = f2f_count + f2p_count + p2p_count

    print(f"Total run.log files found: {total_files_found}")
    print(f"Files with valid metrics: {valid_count}")
    print(f"Total built instances: {total_built_instances}")
    print(f"Total duration: {total_duration:.2f} seconds ({format_seconds(total_duration)})")
    print(f"Total cost: ${total_cost:.6f}")
    print(f"Total tokens: {total_tokens}")
    print(f"Average duration: {avg_duration:.2f} seconds ({format_seconds(avg_duration)})")
    print(f"Average cost: ${avg_cost:.6f}")

    print("")
    print(f"Longest duration: {longest_duration:.2f} seconds ({format_seconds(longest_duration)}) [issue: {extract_issue_number(longest_file)}]")
    print(f"Shortest duration: {shortest_duration:.2f} seconds ({format_seconds(shortest_duration)}) [issue: {extract_issue_number(shortest_file)}]")
    print(f"Most expensive cost: ${most_expensive_cost:.6f} [issue: {extract_issue_number(most_expensive_file)}]")
    print(f"Cheapest cost: ${cheapest_cost:.6f} [issue: {extract_issue_number(cheapest_file)}]")

if __name__ == "__main__":
    main()
