import json
import re
from pathlib import Path

# Path configurations relative to the script location (assuming script is in tools/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = PROJECT_ROOT / "data/issues"
JSON_DIR = PROJECT_ROOT / "conf/dockerbuild/batch_issues.json"


def update_batch_issues():
    # Ensure issues directory exists
    if not BASE_DIR.exists() or not BASE_DIR.is_dir():
        print(f"Error: Directory '{BASE_DIR}' does not exist.")
        return

    # Extract issue ID for natural numerical sorting
    def extract_issue_id(path: Path) -> int:
        match = re.search(r"issue_(\d+)\.json$", path.name)
        return int(match.group(1)) if match else float("inf")

    # Find matching issue files and sort numerically by ID
    issue_files = sorted(
        [
            f for f in BASE_DIR.glob("issue_*.json")
            if extract_issue_id(f) != float("inf")
        ],
        key=extract_issue_id,
    )

    # Convert paths to be relative to PROJECT_ROOT using POSIX slashes
    issue_paths = [
        f.relative_to(PROJECT_ROOT).as_posix() for f in issue_files
    ]

    # Ensure target output directory exists
    JSON_DIR.parent.mkdir(parents=True, exist_ok=True)

    # Prepare JSON payload
    data = {"issues": issue_paths}

    # Write updated JSON file
    with open(JSON_DIR, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully updated '{JSON_DIR}' with {len(issue_paths)} issue file(s).")


if __name__ == "__main__":
    update_batch_issues()