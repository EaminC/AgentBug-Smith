import os
from pathlib import Path
from dotenv import load_dotenv
import subprocess
import sys

def main():
	# Load .env from project root
	project_root = Path(__file__).resolve().parent.parent
	env_path = project_root / ".env"
	if env_path.exists():
		load_dotenv(env_path)
	else:
		print(f"Warning: .env file not found at {env_path}")

	github_token = os.getenv("GITHUB_TOKEN")
	if not github_token:
		print("Error: GITHUB_TOKEN not found in environment.")
		return

	agent_name = input("Enter the agent repo name (e.g: Significant-Gravitas/AutoGPT): ").strip()
	if not agent_name:
		print("Error: agent repo name is required.")
		return

	script_path = project_root / "src" / "issue" / "issue_crawler.py"
	if not script_path.exists():
		print(f"Error: issue_crawler.py not found at {script_path}")
		return

	cmd = [
		sys.executable,
		str(script_path),
		agent_name,
		"--token", github_token,
		"--local-clone",
		"--min-total-lines", "10",
		"--max-total-lines", "200"
	]
	print(f"Running: {' '.join(cmd)}")

	result = subprocess.run(cmd)
	if result.returncode != 0:
		print("issue_crawler.py failed. Aborting filter step.")
		return

	# Run filter_issues.py for each hooked_issue/*/issue.json
	hooked_issue_dir = project_root / "data" / "hooked_issue"
	filter_script = project_root / "src" / "issue" / "filter_issues.py"
	if not filter_script.exists():
		print(f"Error: filter_issues.py not found at {filter_script}")
		return

	# Find all issue.json files in hooked_issue/*/
	for subdir in hooked_issue_dir.iterdir():
		issue_json = subdir / "issue.json"
		if issue_json.exists():
			filter_cmd = [
				sys.executable,
				str(filter_script),
				str(issue_json),
				str(project_root / "data" / "issues")
			]
			print(f"Running: {' '.join(filter_cmd)}")
			subprocess.run(filter_cmd)

if __name__ == "__main__":
	main()
