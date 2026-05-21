#!/usr/bin/env python3
"""
Aggregate issue JSON files under data/issue_agent into a single summary JSON.
Outputs to result/issue_agent_summary.json

This script converts data in data/issue_agent/*.json into a JSON file for SWE-Factory and SWE-Bench-LIVE.

Usage: python tools/aggregate_issue_agents.py
"""
from pathlib import Path
import json
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "issue_agent_35"
OUTPUT_DIR = ROOT
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "issue_agent_summary.json"

summary = []

for p in sorted(INPUT_DIR.glob("*.json")):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Skipping {p}: failed to parse JSON: {e}")
        continue

    # repo: try explicit key, else infer from url
    repo = data.get("repo") or data.get("repository")
    if not repo:
        url = data.get("url") or data.get("html_url")
        if url:
            try:
                parsed = urlparse(url)
                parts = [seg for seg in parsed.path.split("/") if seg]
                if len(parts) >= 2:
                    repo = f"{parts[0]}/{parts[1]}"
            except Exception:
                repo = None
    
    issue_number = data.get("number")

    pr_number = None
    linked = data.get("linked_prs") or data.get("linked_prs_list") or data.get("pull_requests")
    if isinstance(linked, list) and linked:
        # try to find first PR number
        first = linked[0]
        if isinstance(first, dict):
            pr_number = first.get("number")
        else:
            # if entries are integers or strings
            try:
                pr_number = int(first)
            except Exception:
                pr_number = None

    entry = {
        "repo": repo,
        "issue_number": issue_number,
        "pr_number": pr_number
    }
    summary.append(entry)

# sort for determinism
summary = sorted(summary, key=lambda x: (x.get("repo") or "", x.get("issue_number") or 0))

OUTPUT_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {OUTPUT_FILE}")
