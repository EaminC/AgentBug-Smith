"""
count_f2p_issues_groupby_agent.py

This script analyzes issue JSON files in the f2p folder structure, grouping them by agent/repo and counting how many issues have patch tests, do not have patch tests, and the total per agent/repo.

Usage:
    python tools/count_f2p_issues_groupby_agent.py

The script expects the f2p folder to contain subfolders for each issue (e.g., f2p/issue_70_20260512T041132Z/), each containing an issue_*.json file. Each issue JSON should contain a 'url' field and a 'test_paths_in_patch' field.
"""

import os
import json
from collections import defaultdict
from urllib.parse import urlparse

# Path to the f2p folder (relative to project root)
F2P_DIR = "result_history/result_05242026 (50 issues)/f2p"

def get_agent_repo_from_url(url):
    """
    Extract the agent_name/repo from a GitHub issue URL.
    """
    try:
        parts = urlparse(url)
        path_parts = parts.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
    except Exception:
        pass
    return "unknown/unknown"

def main():
    """
    Main function to process all issue JSON files in F2P_DIR, group by agent/repo, and count issues with and without patch tests.
    """
    stats = defaultdict(lambda: {'with_patch_test': 0, 'without_patch_test': 0, 'total': 0})
    for issue_dir in os.listdir(F2P_DIR):
        issue_dir_path = os.path.join(F2P_DIR, issue_dir)
        if not os.path.isdir(issue_dir_path):
            continue
        # Look for issue_*.json in this directory
        json_file = None
        for fname in os.listdir(issue_dir_path):
            if fname.startswith('issue_') and fname.endswith('.json'):
                json_file = os.path.join(issue_dir_path, fname)
                break
        if not json_file:
            continue
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            url = data.get('url', '')
            agent_repo = get_agent_repo_from_url(url)
            test_paths_in_patch = data.get('linked_prs', [{}])[0].get('test_paths_in_patch', [])
            has_patch_test = bool(test_paths_in_patch)
            stats[agent_repo]['total'] += 1
            if has_patch_test:
                stats[agent_repo]['with_patch_test'] += 1
            else:
                stats[agent_repo]['without_patch_test'] += 1
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    # Print results as CSV
    print("Agent/Repo, With Patch Test, Without Patch Test, Total")
    for agent_repo, counts in stats.items():
        print(f"{agent_repo}, {counts['with_patch_test']}, {counts['without_patch_test']}, {counts['total']}")

if __name__ == "__main__":
    main()
