
import os
import json
from collections import Counter
from urllib.parse import urlparse
import fnmatch

# Directory containing the JSON files
ISSUE_AGENT_DIR = os.path.join(os.path.dirname(__file__), '../result_history/result_05132026 (80 issues)')

def extract_agent_repo(url):
    """Extract agentname/repo from a GitHub URL."""
    try:
        parsed = urlparse(url)
        if parsed.netloc != 'github.com':
            return None
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return None
        return f"{path_parts[0]}/{path_parts[1]}"
    except Exception:
        return None


def main():
    counter = Counter()
    # Recursively find all files matching 'issue_*.json'
    for root, _, files in os.walk(ISSUE_AGENT_DIR):
        for fname in fnmatch.filter(files, 'issue_*.json'):
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                url = data.get('url')
                if not url:
                    continue
                agent_repo = extract_agent_repo(url)
                if agent_repo:
                    counter[agent_repo] += 1
            except Exception as e:
                print(f"Error processing {fpath}: {e}")
    for agent_repo, count in counter.most_common():
        print(f"{agent_repo}: {count}")

if __name__ == "__main__":
    main()
