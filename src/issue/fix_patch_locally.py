import json
import subprocess
import os
import shutil
from pathlib import Path

# Define paths assuming this script is run from the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "issue"
TEMP_DIR = PROJECT_ROOT / "data" / "temp_patch_fix"

def remove_readonly(func, path, excinfo):
    """Clear the read-only bit and re-attempt the removal (useful for Windows/Git)."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)

def fix_issue(issue_file_name: str, repo_url: str, pr_number: int):
    # Support both data/ and data/issue/ paths based on your current structure
    issue_path = DATA_DIR / issue_file_name
    if not issue_path.exists():
        issue_path = DATA_DIR / "issue" / issue_file_name

    if not issue_path.exists():
        print(f"Error: Could not find {issue_file_name}")
        return

    print(f"Fixing {issue_file_name} locally...")

    # 1. Load the JSON
    with open(issue_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    pr_data = None
    for pr in data.get('linked_prs', []):
        if pr.get('number') == pr_number:
            pr_data = pr
            break
            
    if not pr_data or not pr_data.get('base_sha'):
        print("Error: Could not find the PR or base_sha in the JSON file.")
        return
        
    known_base_sha = pr_data['base_sha']
    print(f"Found base_sha in JSON: {known_base_sha[:8]}")
    
    # 2. Setup a temporary git clone
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, onerror=remove_readonly)
    
    print(f"Cloning {repo_url} into {TEMP_DIR.name}...")
    subprocess.run(["git", "clone", repo_url, str(TEMP_DIR)], check=True, capture_output=True)
    
    # 3. Fetch the PR 
    print(f"Fetching PR #{pr_number}...")
    subprocess.run(
        ["git", "fetch", "origin", f"pull/{pr_number}/head:pr-{pr_number}"], 
        cwd=str(TEMP_DIR), check=True, capture_output=True
    )
    
    # 4. Generate the patch locally comparing the EXACT base_sha to the PR head
    print(f"Generating full native git diff from {known_base_sha[:8]}...")
    patch_proc = subprocess.run(
        ["git", "diff", known_base_sha, f"pr-{pr_number}"], 
        cwd=str(TEMP_DIR), capture_output=True, text=True, check=True
    )
    full_patch = patch_proc.stdout

    # 5. Update the JSON
    pr_data['patch'] = full_patch
    with open(issue_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {issue_file_name} with a {len(full_patch)}-character patch!")

    # Cleanup
    print("Cleaning up temporary directory...")
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR, onerror=remove_readonly)
    print("Done.")

if __name__ == "__main__":
    fix_issue("issue_1277.json", "https://github.com/agentscope-ai/agentscope", 1290)