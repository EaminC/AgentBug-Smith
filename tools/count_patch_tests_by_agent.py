import os
import json
from collections import defaultdict
from urllib.parse import urlparse

# Path to the issues folder
ISSUES_DIR = "data/issues_80"

def get_agent_repo_from_url(url):
    """Extract agent_name/repo from GitHub issue URL."""
    try:
        parts = urlparse(url)
        path_parts = parts.path.strip('/').split('/')
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"
    except Exception:
        pass
    return "unknown/unknown"

def main():
    stats = defaultdict(lambda: {'with_patch_test': 0, 'without_patch_test': 0, 'total': 0})
    for fname in os.listdir(ISSUES_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(ISSUES_DIR, fname)
        try:
            with open(fpath, 'r') as f:
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
            print(f"Error processing {fname}: {e}")
    print("Agent/Repo, With Patch Test, Without Patch Test, Total")
    for agent_repo, counts in stats.items():
        print(f"{agent_repo}, {counts['with_patch_test']}, {counts['without_patch_test']}, {counts['total']}")

if __name__ == "__main__":
    main()
