#!/usr/bin/env python3
"""
从 data/issue-filtered 生成 RQ2 的 issue_pr_map.json（并在每条记录里附加 n 次判断结果）。

输出：
- out_json：包含 repo/issue_number/pr_number/judgments/... 的完整列表
- out_all_yes_json：仅包含 judgments 全为 "yes" 的子集

判断来源：
- quick_check（默认）：复用 src/issue-hook/quick_check.check_agent_issue_only（会访问 GitHub API + 调用 LLM）
- file_ai_judgment：使用 issue-filtered 文件中的 ai_judgment.is_agent_issue（离线/快速）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal


JudgeSource = Literal["quick_check", "file_ai_judgment"]


def _find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "src").exists() and (p / "Baseline").exists():
            return p
    return start


def _load_dotenv_if_present(project_root: Path) -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def _require_forge_api_key_if_needed(judge_source: JudgeSource) -> None:
    if judge_source != "quick_check":
        return
    api_key = os.getenv("FORGE_API_KEY", "").strip().strip('"').strip("'")
    if api_key:
        return
    raise SystemExit(
        "Error: FORGE_API_KEY 未配置。judge-source=quick_check 会调用 LLM，需在 SWEGENT-BENCH/.env 中配置：\n"
        "  FORGE_API_KEY=your-key\n"
        "可选：FORGE_BASE_URL、MODEL；建议配置 GITHUB_TOKEN 以免 GitHub API 限流。\n"
        "如果你只想离线生成/复用 issue-filtered 里的 ai_judgment，请加参数：--judge-source file_ai_judgment"
    )


_GITHUB_ISSUE_URL_RE = re.compile(r"^https?://github\.com/([^/]+/[^/]+)/issues/(\d+)(?:/.*)?$")
_GITHUB_PR_URL_RE = re.compile(r"^https?://github\.com/([^/]+/[^/]+)/pull/(\d+)(?:/.*)?$")


def _parse_repo_from_url(url: str | None) -> str | None:
    if not url:
        return None
    m = _GITHUB_ISSUE_URL_RE.match(url.strip())
    if m:
        return m.group(1)
    m = _GITHUB_PR_URL_RE.match(url.strip())
    if m:
        return m.group(1)
    return None


def _safe_int(x: Any) -> int | None:
    try:
        return int(x)
    except Exception:
        return None


def _pick_pr_number(linked_prs: list[dict[str, Any]] | None) -> int | None:
    if not linked_prs:
        return None

    prs = []
    for pr in linked_prs:
        num = _safe_int(pr.get("number"))
        if num is None:
            continue
        prs.append(
            {
                "number": num,
                "merged": bool(pr.get("merged", False)),
                "base_branch": (pr.get("base_branch") or "").strip().lower(),
            }
        )
    if not prs:
        return None

    def score(p: dict[str, Any]) -> tuple[int, int, int]:
        merged = 1 if p["merged"] else 0
        main = 1 if p["base_branch"] in {"main", "master"} else 0
        # 排序：优先 merged+main/master，其次 merged，其次其它；最后用 PR number 小的更稳定
        return (merged, main, -p["number"])

    prs.sort(key=score, reverse=True)
    return int(prs[0]["number"])


@dataclass(frozen=True)
class VoteResult:
    judgments: list[str]  # "yes"/"no"
    yes_count: int


def _run_votes_quick_check(
    project_root: Path,
    repo: str,
    issue_number: int,
    n: int,
    github_token: str | None,
    sleep_s: float,
    store_llm_response: bool,
) -> tuple[VoteResult, list[str] | None]:
    sys.path.insert(0, str(project_root / "src" / "issue-hook"))
    sys.path.insert(0, str(project_root / "src"))
    from quick_check import check_agent_issue_only  # type: ignore

    judgments: list[str] = []
    llm_responses: list[str] = []
    for _ in range(n):
        is_agent, llm_response, _ = check_agent_issue_only(repo, issue_number, github_token)
        judgments.append("yes" if is_agent else "no")
        if store_llm_response:
            llm_responses.append((llm_response or "").strip())
        if sleep_s > 0:
            time.sleep(sleep_s)

    yes_count = sum(1 for j in judgments if j == "yes")
    return VoteResult(judgments=judgments, yes_count=yes_count), (llm_responses if store_llm_response else None)


def _run_votes_file_ai_judgment(issue_obj: dict[str, Any], n: int) -> VoteResult:
    ai_judgment = issue_obj.get("ai_judgment") or {}
    if not isinstance(ai_judgment, dict):
        ai_judgment = {}
    is_agent = bool(ai_judgment.get("is_agent_issue", False))
    judgments = ["yes" if is_agent else "no"] * n
    yes_count = n if is_agent else 0
    return VoteResult(judgments=judgments, yes_count=yes_count)


def _iter_issue_files(issue_dir: Path) -> Iterable[Path]:
    files = sorted(issue_dir.glob("*.json"), key=lambda p: p.name)
    # 若文件名形如 issue_123.json，则按数字排序更直观
    def num_key(p: Path) -> tuple[int, str]:
        m = re.search(r"(\d+)", p.stem)
        return (int(m.group(1)) if m else 10**18, p.name)

    return sorted(files, key=num_key)


def _backup_if_exists(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak.{ts}")
    path.rename(backup)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = _find_project_root(script_dir)

    parser = argparse.ArgumentParser(
        description="从 data/issue-filtered 生成 issue_pr_map.json，并为每条记录附加 n 次 yes/no 判断结果"
    )
    parser.add_argument(
        "--issue-dir",
        default=str(project_root / "data" / "issue-filtered"),
        help="输入目录（包含 issue_*.json）",
    )
    parser.add_argument(
        "--out-json",
        default=str(project_root / "Baseline" / "RQ2" / "issue_pr_map.json"),
        help="输出：完整映射 JSON（会自动备份同名旧文件）",
    )
    parser.add_argument(
        "--out-all-yes-json",
        default=str(project_root / "Baseline" / "RQ2" / "issue_pr_map_all_yes.json"),
        help='输出：仅包含 judgments 全为 "yes" 的子集 JSON（会自动备份同名旧文件）',
    )
    parser.add_argument("--n", type=int, default=5, help="每个 issue 运行判断次数（默认 5；设为 0 则不生成 judgments）")
    parser.add_argument(
        "--judge-source",
        choices=["quick_check", "file_ai_judgment"],
        default="quick_check",
        help="判断来源：quick_check=在线 LLM + GitHub；file_ai_judgment=复用本地 ai_judgment",
    )
    parser.add_argument("--token", default=None, help="GitHub token（或使用环境变量 GITHUB_TOKEN）")
    parser.add_argument("--sleep", type=float, default=0.0, help="每次 quick_check 之间 sleep 秒数（防限流/降速）")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前 N 个 issue（用于快速试跑）")
    parser.add_argument(
        "--store-llm-response",
        action="store_true",
        help="在输出 JSON 中额外保存每次判断的 llm_responses（会明显增大文件体积）",
    )
    args = parser.parse_args()

    issue_dir = Path(args.issue_dir)
    if not issue_dir.exists():
        raise SystemExit(f"Error: issue-dir not found: {issue_dir}")

    _load_dotenv_if_present(project_root)
    judge_source: JudgeSource = args.judge_source
    _require_forge_api_key_if_needed(judge_source)

    github_token = args.token or os.getenv("GITHUB_TOKEN")
    n = int(args.n)
    if n < 0:
        raise SystemExit("Error: --n 不能为负数")

    out_json = Path(args.out_json)
    out_all_yes_json = Path(args.out_all_yes_json)

    records: list[dict[str, Any]] = []
    all_yes_records: list[dict[str, Any]] = []

    issue_files = list(_iter_issue_files(issue_dir))
    if args.limit is not None:
        issue_files = issue_files[: max(0, int(args.limit))]

    for idx, fp in enumerate(issue_files, start=1):
        try:
            issue_obj = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        issue_url = issue_obj.get("url")
        repo = _parse_repo_from_url(issue_url)
        issue_number = _safe_int(issue_obj.get("number"))
        pr_number = _pick_pr_number(issue_obj.get("linked_prs"))

        if not repo or issue_number is None or pr_number is None:
            continue

        rec: dict[str, Any] = {
            "repo": repo,
            "issue_number": issue_number,
            "pr_number": pr_number,
        }

        if n > 0:
            if judge_source == "quick_check":
                vote_res, llm_responses = _run_votes_quick_check(
                    project_root=project_root,
                    repo=repo,
                    issue_number=issue_number,
                    n=n,
                    github_token=github_token,
                    sleep_s=float(args.sleep),
                    store_llm_response=bool(args.store_llm_response),
                )
                rec["judgments"] = vote_res.judgments
                rec["yes_count"] = vote_res.yes_count
                if llm_responses is not None:
                    rec["llm_responses"] = llm_responses
            else:
                vote_res = _run_votes_file_ai_judgment(issue_obj, n=n)
                rec["judgments"] = vote_res.judgments
                rec["yes_count"] = vote_res.yes_count

            rec["all_yes"] = bool(vote_res.yes_count == n)

        records.append(rec)

        if n > 0 and rec.get("all_yes") is True:
            all_yes_records.append(rec)

        if idx % 25 == 0:
            print(f"[{idx}/{len(issue_files)}] collected={len(records)} all_yes={len(all_yes_records)} last={repo}#{issue_number}")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_all_yes_json.parent.mkdir(parents=True, exist_ok=True)
    _backup_if_exists(out_json)
    _backup_if_exists(out_all_yes_json)

    out_json.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_all_yes_json.write_text(json.dumps(all_yes_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Done.\n- out_json: {out_json} ({len(records)} records)\n- out_all_yes_json: {out_all_yes_json} ({len(all_yes_records)} records)")


if __name__ == "__main__":
    main()

