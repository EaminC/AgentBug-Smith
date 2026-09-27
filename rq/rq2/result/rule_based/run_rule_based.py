#!/usr/bin/env python3
"""
RQ2 方法 1：复用 src/issue-hook/quick_check 的 check_agent_issue_only（AI 判断，不检查合并/关联 PR 等）。
结果写入：<timestamp>/rule_based/<reponame>-<issue_number>.txt，内容为 yes 或 no。
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

from quick_check import check_agent_issue_only

_ISSUE_PR_MAP_ENV = os.getenv("RQ2_ISSUE_PR_MAP")
if _ISSUE_PR_MAP_ENV and Path(_ISSUE_PR_MAP_ENV).exists():
    DEFAULT_ISSUE_PR_MAP = _ISSUE_PR_MAP_ENV
elif (_RQ2_DIR / "issue_pr_map.json").exists():
    DEFAULT_ISSUE_PR_MAP = str(_RQ2_DIR / "issue_pr_map.json")
else:
    _p = _PROJECT_ROOT.parent / "swe-factory" / "baseline" / "issue_pr_map.json"
    DEFAULT_ISSUE_PR_MAP = str(_p)


def _load_issue_pr_map(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _ensure_out_dir(base: Path, subdir: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / ts / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="RQ2 方法1: 复用 quick_check 仅做 agent issue 判断（AI，不检查合并等）"
    )
    parser.add_argument("--issue-pr-map", default=DEFAULT_ISSUE_PR_MAP, help="Path to issue_pr_map.json")
    parser.add_argument("--out-dir", default=None, help="Base output dir (default: rule_based/ under RQ2)")
    parser.add_argument("--token", default=None, help="GitHub token (or GITHUB_TOKEN)")
    args = parser.parse_args()

    issue_pr_map_path = args.issue_pr_map
    if not Path(issue_pr_map_path).exists():
        print(f"Error: issue_pr_map not found: {issue_pr_map_path}", file=sys.stderr)
        sys.exit(1)

    items = _load_issue_pr_map(issue_pr_map_path)
    base_out = Path(args.out_dir) if args.out_dir else _SCRIPT_DIR
    out_dir = _ensure_out_dir(base_out, "rule_based")

    for i, rec in enumerate(items):
        repo = rec.get("repo") or ""
        issue_number = rec.get("issue_number")
        if not repo or issue_number is None:
            continue
        reponame = repo.replace("/", "-")
        fname = f"{reponame}-{issue_number}.txt"
        out_file = out_dir / fname

        is_agent, llm_response, _ = check_agent_issue_only(repo, issue_number, args.token)
        result = "yes" if is_agent else "no"
        print(f"[{i+1}/{len(items)}] {repo}#{issue_number} -> {result}")
        # 第一行：最终判断；第二行：LLM 原始输出
        out_file.write_text(result + "\n" + (llm_response or ""), encoding="utf-8")

    print(f"Done. Outputs under: {out_dir}")


if __name__ == "__main__":
    main()
