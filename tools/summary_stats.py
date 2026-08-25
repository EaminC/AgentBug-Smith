"""
summary_stats.py
----------------

This script recursively searches for all run directories in the result folder.
It extracts the total duration from `run.log` and exact cost/token usage from `agentsmith_stat.json`.
Outputs the total and average duration, cost, and detailed token breakdown across all valid logs.

Usage:
    python tools/summary_stats.py
"""
import os
import json
import re

RESULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'results/kimi-k2.5/result_25'))
RUN_LOG_FILENAME = 'run.log'
STAT_JSON_FILENAME = 'agentsmith_stat.json'

def find_summary_dirs(root_dir):
    """
    Recursively find all directories containing a run.log file.
    Returns a list of directory paths.
    """
    runlog_dirs = []
    for dirpath, _, filenames in os.walk(root_dir):
        if RUN_LOG_FILENAME in filenames:
            runlog_dirs.append(dirpath)
    return runlog_dirs

def extract_metrics(dirpath):
    """
    Extract duration from run.log and cost/tokens from agentsmith_stat.json.
    """
    runlog_file = os.path.join(dirpath, RUN_LOG_FILENAME)
    stat_file = os.path.join(dirpath, STAT_JSON_FILENAME)
    
    duration = None
    cost = None
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    
    # 1. Extract Duration from run.log
    try:
        with open(runlog_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in reversed(lines):
            dur_match = re.search(r'Total Duration: [^\(]*\(([-\d.]+) seconds\)', line)
            if dur_match:
                duration = float(dur_match.group(1))
                break
    except Exception as e:
        print(f"Error reading {runlog_file}: {e}")

    # 2. Extract exact tokens and cost from agentsmith_stat.json
    if os.path.exists(stat_file):
        try:
            with open(stat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check for end_stats or fallback to usage_delta
                stats_block = None
                if "end_stats" in data and len(data["end_stats"]) > 0:
                    stats_block = data["end_stats"][0]
                elif "usage_delta" in data:
                    stats_block = data["usage_delta"]
                    
                if stats_block:
                    cost = stats_block.get("cost", 0.0)
                    input_tokens = stats_block.get("input_tokens", 0)
                    output_tokens = stats_block.get("output_tokens", 0)
                    total_tokens = stats_block.get("total_tokens", 0)
        except Exception as e:
            print(f"Error reading {stat_file}: {e}")

    return duration, cost, input_tokens, output_tokens, total_tokens

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
    run_dirs = find_summary_dirs(RESULT_DIR)
    total_files_found = len(run_dirs)
    
    total_duration = 0
    total_cost = 0
    tot_input_tokens = 0
    tot_output_tokens = 0
    tot_total_tokens = 0
    valid_count = 0
    
    durations = []  # List of (duration, dirpath)
    costs = []      # List of (cost, dirpath)
    
    for d in run_dirs:
        duration, cost, in_tok, out_tok, tot_tok = extract_metrics(d)
        
        if duration is not None and cost is not None:
            total_duration += duration
            total_cost += cost
            tot_input_tokens += in_tok
            tot_output_tokens += out_tok
            tot_total_tokens += tot_tok
            
            valid_count += 1
            durations.append((duration, d))
            costs.append((cost, d))
            
    if valid_count == 0:
        print("No valid runs found with both duration and cost.")
        print(f"Total run directories found: {total_files_found}")
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
        return match.group(0) if match else os.path.basename(filepath)

    f2f_count = count_subfolders(os.path.join(RESULT_DIR, 'f2f'))
    f2p_count = count_subfolders(os.path.join(RESULT_DIR, 'f2p'))
    p2p_count = count_subfolders(os.path.join(RESULT_DIR, 'p2p'))
    total_built_instances = f2f_count + f2p_count + p2p_count

    print(f"Total run directories found: {total_files_found}")
    print(f"Directories with valid metrics: {valid_count}")
    print(f"Total built instances: {total_built_instances}")
    print(f"Total duration: {total_duration:.2f} seconds ({format_seconds(total_duration)})")
    print(f"Total cost: ${total_cost:.6f}")
    
    print(f"Total input_tokens: {tot_input_tokens:,}")
    print(f"Total output_tokens: {tot_output_tokens:,}")
    print(f"Total total_tokens: {tot_total_tokens:,}")
    
    print(f"Average duration: {avg_duration:.2f} seconds ({format_seconds(avg_duration)})")
    print(f"Average cost: ${avg_cost:.6f}")

    print("")
    print(f"Longest duration: {longest_duration:.2f} seconds ({format_seconds(longest_duration)}) [issue: {extract_issue_number(longest_file)}]")
    print(f"Shortest duration: {shortest_duration:.2f} seconds ({format_seconds(shortest_duration)}) [issue: {extract_issue_number(shortest_file)}]")
    print(f"Most expensive cost: ${most_expensive_cost:.6f} [issue: {extract_issue_number(most_expensive_file)}]")
    print(f"Cheapest cost: ${cheapest_cost:.6f} [issue: {extract_issue_number(cheapest_file)}]")

if __name__ == "__main__":
    main()