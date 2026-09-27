#!/usr/bin/env python3
"""
RQ2 方法 2：使用 Claude Code Agent 判断 agent issue
复用 src/issue-hook 的 fetch_issue_for_rq2、build_agent_issue_prompt、load_agent_criteria，
与 forge_ai 相同的 prompt；循环调用 claude CLI 得 yes/no。
结果写入 <时间戳>/claude/<reponame>-<issue_number>.txt
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

_SCRIPT_DIR = Path(__file__).resolve().parent
_RQ2_DIR = _SCRIPT_DIR.parent
_BASELINE_DIR = _RQ2_DIR.parent
_PROJECT_ROOT = _BASELINE_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src" / "issue-hook"))
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from issue_crawler import fetch_issue_for_rq2, build_agent_issue_prompt, load_agent_criteria

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


def _call_claude_and_get_yes_no(system_prompt: str, user_message: str) -> tuple:
    """调用 claude CLI，传入与 forge 一致的 system + user prompt，解析 yes/no。返回 (answer, raw_output)。"""
    prompt = f"{system_prompt}\n\n---\n\n{user_message}\n\nReply with exactly one word: yes or no."
    try:
        result = subprocess.run(
            ["claude", "-p", "--dangerously-skip-permissions", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=_SCRIPT_DIR,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        raw_output = (stdout + "\n" + stderr).strip() or ""
        if result.returncode != 0 and stderr:
            print(f"  claude stderr: {stderr[:500]}", file=sys.stderr)
        combined = (stdout + "\n" + stderr).lower()
        for line in combined.splitlines():
            line = line.strip()
            if line in ("yes", "no"):
                return line, raw_output
            if line.startswith("yes"):
                return "yes", raw_output
            if line.startswith("no"):
                return "no", raw_output
        if "yes" in combined:
            return "yes", raw_output
        return "no", raw_output
    except subprocess.TimeoutExpired:
        print("  claude timeout", file=sys.stderr)
        return "no", ""
    except FileNotFoundError:
        print("  claude CLI not found; install it first", file=sys.stderr)
        return "no", ""
    except Exception as e:
        print(f"  claude error: {e}", file=sys.stderr)
        return "no", ""


def _ensure_out_dir(base: Path, subdir: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / ts / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RQ2 claude agent: judge agent issue via Claude CLI, reuse issue-hook")
    parser.add_argument("--issue-pr-map", default=DEFAULT_ISSUE_PR_MAP, help="Path to issue_pr_map.json")
    parser.add_argument("--out-dir", default=None, help="Base output dir (default: claude_agent/ under RQ2)")
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
    out_dir = _ensure_out_dir(base_out, "claude")

    criteria = load_agent_criteria()

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
        answer, raw_output = _call_claude_and_get_yes_no(system_prompt, user_message)
        # 第一行：最终判断；第二行：LLM/Claude 原始输出
        out_file.write_text(answer + "\n" + (raw_output or ""), encoding="utf-8")
        print(f"[{i+1}/{len(items)}] {repo}#{issue_number} -> {answer}")

    print(f"Done. Outputs under: {out_dir}")


if __name__ == "__main__":
    main()
