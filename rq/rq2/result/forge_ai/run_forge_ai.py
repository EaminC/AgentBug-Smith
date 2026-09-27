#!/usr/bin/env python3
"""
RQ2 方法 3：使用裸 AI（Forge API）判断 agent issue
复用 src/issue-hook 的 fetch_issue_for_rq2、build_agent_issue_prompt、load_agent_criteria，
以及 src/forge/api.py 的 LLMClient。结果写入 <时间戳>/forge/<reponame>-<issue_number>.txt
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

_SCRIPT_DIR = Path(__file__).resolve().parent
_RQ2_DIR = _SCRIPT_DIR.parent
_BASELINE_DIR = _RQ2_DIR.parent
_PROJECT_ROOT = _BASELINE_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "issue-hook"))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from issue_crawler import fetch_issue_for_rq2, build_agent_issue_prompt, load_agent_criteria
from forge.api import LLMClient

_ISSUE_PR_MAP_ENV = os.getenv("RQ2_ISSUE_PR_MAP")
if _ISSUE_PR_MAP_ENV and Path(_ISSUE_PR_MAP_ENV).exists():
    DEFAULT_ISSUE_PR_MAP = _ISSUE_PR_MAP_ENV
elif (_RQ2_DIR / "issue_pr_map.json").exists():
    DEFAULT_ISSUE_PR_MAP = str(_RQ2_DIR / "issue_pr_map.json")
else:
    DEFAULT_ISSUE_PR_MAP = str(_PROJECT_ROOT.parent / "swe-factory" / "baseline" / "issue_pr_map.json")


def _load_issue_pr_map(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _parse_yes_no(response: str) -> str:
    r = (response or "").strip().lower()
    for line in r.splitlines():
        line = line.strip()
        if line in ("yes", "no"):
            return line
        if line.startswith("yes"):
            return "yes"
        if line.startswith("no"):
            return "no"
    if "yes" in r:
        return "yes"
    return "no"


def _ensure_out_dir(base: Path, subdir: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / ts / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RQ2 forge AI: judge agent issue via Forge API, reuse issue-hook")
    parser.add_argument("--issue-pr-map", default=DEFAULT_ISSUE_PR_MAP, help="Path to issue_pr_map.json")
    parser.add_argument("--out-dir", default=None, help="Base output dir (default: forge_ai/ under RQ2)")
    parser.add_argument("--token", default=None, help="GitHub token (or GITHUB_TOKEN)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of issues to process (default: all)")
    args = parser.parse_args()

    issue_pr_map_path = args.issue_pr_map
    if not Path(issue_pr_map_path).exists():
        print(f"Error: issue_pr_map not found: {issue_pr_map_path}", file=sys.stderr)
        sys.exit(1)

    items = _load_issue_pr_map(issue_pr_map_path)
    if args.limit is not None:
        items = items[: args.limit]
    base_out = Path(args.out_dir) if args.out_dir else _SCRIPT_DIR
    out_dir = _ensure_out_dir(base_out, "forge")

    criteria = load_agent_criteria()
    llm = LLMClient()

    for i, rec in enumerate(items):
        repo = rec.get("repo") or ""
        issue_number = rec.get("issue_number")
        if not repo or issue_number is None:
            continue
        reponame = repo.replace("/", "-")
        fname = f"{reponame}-{issue_number}.txt"
        out_file = out_dir / fname

        issue = fetch_issue_for_rq2(repo, issue_number, args.token)
        if not issue:
            out_file.write_text("no\n", encoding="utf-8")
            print(f"[{i+1}/{len(items)}] {repo}#{issue_number} fetch failed -> no")
            continue

        system_prompt, user_message = build_agent_issue_prompt(issue, repo, issue_number, criteria)
        response = ""
        try:
            response = llm.simple_chat(
                user_message=user_message,
                system_prompt=system_prompt,
                temperature=0.2,
            )
            answer = _parse_yes_no(response)
        except Exception as e:
            print(f"  LLM error for {repo}#{issue_number}: {e}", file=sys.stderr)
            answer = "no"
        # 第一行：最终判断；第二行：LLM 原始输出
        out_file.write_text(answer + "\n" + (response or ""), encoding="utf-8")
        print(f"[{i+1}/{len(items)}] {repo}#{issue_number} -> {answer}")

    print(f"Done. Outputs under: {out_dir}")


if __name__ == "__main__":
    main()
