import subprocess
import json
import os
import sys
from pathlib import Path
from time import sleep
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src')))
from stats.entry import StatsTool
from tabnanny import verbose

load_dotenv()
YOUR_TOKEN = os.getenv('GITHUB_TOKEN')

def run_command(cmd, desc):
    print(f"\n{'='*60}\nRunning: {desc}\n{'='*60}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    if rc != 0:
        print(f"[X] Command failed: {' '.join(cmd)}")
        sys.exit(1)
    print(f"[OK] Finished: {desc}\n{'='*60}")

def main():
    StatsTool(verbose=verbose).run("start")

    # Step 1: Run github/main.py
    run_command(
        ["python", "src/repo-hook/github/main.py", "--github-token", YOUR_TOKEN],
        "Collecting agent repos from awesome lists"
    )

    # Step 2: Run github_archive/main.py
    run_command(
        ["python", "src/repo-hook/github_archive/main.py", "--time-window", "1h", "--min-stars", "50", "--github-token", YOUR_TOKEN],
        "Collecting agent repos from GitHub Archive"
    )

    # Step 3: Run repo_merge/main.py
    run_command(
        ["python", "src/repo-hook/repo_merge/main.py"],
        "Merging agent repository data"
    )

    # Step 4: Read agent_repo.json and run issue_crawler.py for each agent
    agent_repo_path = Path("data/hooked_repo/agent_repo.json")
    if not agent_repo_path.exists():
        print(f"[X] agent_repo.json not found at {agent_repo_path}")
        sys.exit(1)

    with open(agent_repo_path, "r", encoding="utf-8") as f:
        agent_list = json.load(f)

    total_agents = len(agent_list)
    print(f"\n{'='*60}\nStarting issue crawling for {total_agents} agents\n{'='*60}")

    for idx, agent_name in enumerate(agent_list, 1):
        percent = int((idx / total_agents) * 100)
        print(f"\n[{idx}/{total_agents}] ({percent}%) Running issue_crawler.py for: {agent_name}")
        cmd = [
            "python", "src/issue-hook/issue_crawler.py", agent_name,
            "--token", YOUR_TOKEN,
            "--local-clone"
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc != 0:
            print(f"[X] issue_crawler.py failed for {agent_name}")
        else:
            print(f"[OK] Finished issue_crawler.py for {agent_name}")

    print(f"\n{'='*60}\nAll processes completed!\n{'='*60}")
    StatsTool(verbose=verbose).run("end")

if __name__ == "__main__":
    main()