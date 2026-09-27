import os
import subprocess
from pathlib import Path

def main():
    workspace_root = Path(__file__).parent.parent.parent
    hooked_issue_dir = workspace_root / "data" / "hooked_issue_up_success"
    filter_issues_script = workspace_root / "src" / "test-gen" / "filter_issues.py"
    output_dir = workspace_root / "data" / "issue-filtered"

    # Loop through each agent directory
    for agent_name in os.listdir(hooked_issue_dir):
        agent_path = hooked_issue_dir / agent_name
        issue_json = agent_path / "issue.json"
        if issue_json.exists():
            print(f"Processing: {issue_json}")
            cmd = [
                "python",
                str(filter_issues_script),
                str(issue_json),
                str(output_dir)
            ]
            subprocess.run(cmd, check=True)
            print(f"[OK] Success: {issue_json}")
        else:
            print(f"Skipped: {issue_json} (not found)")

if __name__ == "__main__":
    main()