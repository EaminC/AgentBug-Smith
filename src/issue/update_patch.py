import json
import requests
import sys
import os
import re
import glob
from pathlib import Path

# Use the absolute path to your data folder for consistency
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "issue"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def sanitize_patch(raw_patch: str) -> str:
    """
    Performs deep sanitization of the patch text to satisfy git apply requirements.
    """
    if not raw_patch:
        return ""
    # 1. Replace non-breaking spaces with standard spaces
    clean = raw_patch.replace('\u00a0', ' ')
    # 2. Standardize line endings to Unix (LF)
    clean = clean.replace('\r\n', '\n')
    # 3. Ensure the patch ends with a newline
    if not clean.endswith('\n'):
        clean += '\n'
    return clean

def parse_test_paths(patch_text):
    """
    Parses a unified diff to find paths of files that look like tests.
    """
    if not patch_text:
        return []
    
    # Captures the 'new' file path from the diff line: +++ b/path/to/file
    new_file_pattern = re.compile(r'^\+\+\+ b/(.+)$', re.MULTILINE)
    all_files = new_file_pattern.findall(patch_text)
    
    test_paths = []
    for path in all_files:
        filename = os.path.basename(path)
        # Filters for common Python test naming conventions
        is_test_file = (
            filename.startswith("test_") or 
            filename.endswith("_test.py") or 
            "tests/" in path.lower() or 
            "testing/" in path.lower()
        )
        if is_test_file:
            test_paths.append(path)
            
    return sorted(list(set(test_paths)))

def get_pr_metadata(pr_url):
    """
    Fetches the PR metadata and full diff securely via the GitHub API.
    """
    # Convert Web URL to API URL
    api_url = pr_url.replace("github.com", "api.github.com/repos").replace("/pull/", "/pulls/")
    
    # 1. Headers for getting the JSON metadata (for base_sha)
    headers_meta = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else ""
    }
    
    # 2. CRITICAL FIX: Headers for getting the raw DIFF reliably via the API
    headers_diff = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else ""
    }

    try:
        # Fetch correct base_sha from API
        meta_resp = requests.get(api_url, headers=headers_meta, timeout=30)
        correct_base_sha = None
        if meta_resp.status_code == 200:
            pr_data = meta_resp.json()
            correct_base_sha = pr_data.get('base', {}).get('sha')

        # Fetch Full Patch via API (Bypasses web scraping rate limits)
        diff_resp = requests.get(api_url, headers=headers_diff, timeout=30)
        
        if diff_resp.status_code == 200:
            return sanitize_patch(diff_resp.text), correct_base_sha
        else:
            print(f"   [Error] API Diff returned {diff_resp.status_code}")
            return None, correct_base_sha
            
    except Exception as e:
        print(f"   [Error] API call failed: {e}")
        return None, None

def update_json_patch(file_path):
    print(f"Cleaning: {os.path.basename(file_path)}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data.get('linked_prs'): return

    updated = False
    for pr in data['linked_prs']:
        if pr.get('url') and 'github.com' in pr['url'] and '/pull/' in pr['url']:
            raw_diff, correct_sha = get_pr_metadata(pr['url'])
            
            if correct_sha and pr.get('base_sha') != correct_sha:
                pr['base_sha'] = correct_sha
                updated = True
                print(f"   [Updated] base_sha -> {correct_sha[:8]}")
                
            if raw_diff:
                # Update the patch and ensure test paths are recalculated
                pr['patch'] = raw_diff
                pr['test_paths_in_patch'] = parse_test_paths(raw_diff)
                updated = True

    if updated:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"   [Done] {os.path.basename(file_path)} is now sanitized.")

def main():
    # The loop: finds all issue_*.json files in your project data directory
    pattern = os.path.join(DATA_DIR, "issue*.json")
    json_files = glob.glob(pattern)
    
    if not json_files:
        print(f"No files found matching {pattern}")
        return

    print(f"Found {len(json_files)} files. Starting batch update...")
    for json_file in json_files:
        update_json_patch(json_file)

if __name__ == "__main__":
    main()