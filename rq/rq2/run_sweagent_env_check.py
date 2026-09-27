#!/usr/bin/env python3
"""
用 SWE-agent 跑 issue_pr_map.json 里的 (repo, issue)，统计「多少环境能跑」。
使用本地 OpenAI API Key（可从 .swefactory.env 或环境变量读取）。
每个 issue 限制成本（默认 0.5 美元）以快速判断环境是否可用。
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 默认路径
RQ2_DIR = Path(__file__).resolve().parent
ISSUE_PR_MAP_PATH = RQ2_DIR / "issue_pr_map.json"
SWEAGENT_CONFIG = Path("/home/cc/SWE-agent/config/default.yaml")
# 可选：从 .swefactory.env 加载（export KEY='val' 格式）
ENV_FILES = [
    Path.home() / ".swefactory.env",
    RQ2_DIR / ".swefactory.env",
    RQ2_DIR / ".env",
]


def _load_export_env(path: Path) -> dict:
    """解析 export KEY='val' 或 export KEY=\"val\" 或 KEY=val，返回 {KEY: val}。"""
    out = {}
    if not path.is_file():
        return out
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 去掉前导 export
        s = line
        if s.lower().startswith("export "):
            s = s[7:].strip()
        # KEY='val' / KEY="val" / KEY=val
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", s)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            val = val[1:-1]
        out[key] = val
    return out


def _apply_env_to_process(env: dict) -> dict:
    """把 env 合并进 os.environ，返回适合 subprocess 的 env。"""
    import os
    base = os.environ.copy()
    for k, v in env.items():
        base[k] = v
    # litellm 自定义 OpenAI base 常用 OPENAI_API_BASE
    if "OPENAI_BASE_URL" in base and "OPENAI_API_BASE" not in base:
        base["OPENAI_API_BASE"] = base["OPENAI_BASE_URL"]
    return base


def load_issue_pr_map(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def issue_key(rec: dict) -> str:
    repo = (rec.get("repo") or "").replace("/", "-")
    return f"{repo}-{rec.get('issue_number', '')}"


def run_sweagent_once(
    repo: str,
    issue_number: int,
    env: dict,
    *,
    config_path: Path,
    cost_limit: float = 0.5,
    timeout_sec: int = 600,
) -> tuple[bool, str]:
    """
    对单个 (repo, issue) 跑一次 sweagent run。
    返回 (是否成功, 简短原因)。
    """
    repo_url = f"https://github.com/{repo}"
    issue_url = f"https://github.com/{repo}/issues/{issue_number}"
    cmd = [
        sys.executable, "-m", "sweagent", "run",
        "--config", str(config_path),
        "--agent.model.name", "gpt-4o",
        "--agent.model.per_instance_cost_limit", str(cost_limit),
        "--env.repo.github_url", repo_url,
        "--problem_statement.github_url", issue_url,
    ]
    try:
        proc = subprocess.run(
            cmd,
            env=_apply_env_to_process(env),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd="/home/cc/SWE-agent",
        )
        if proc.returncode == 0:
            return True, "ok"
        err = (proc.stderr or proc.stdout or "")
        if "ModuleNotFoundError: No module named 'swerex'" in err:
            return False, "未安装 swe-rex，请运行: cd /home/cc/SWE-agent && pip install -e ."
        return False, f"exit={proc.returncode} {(err[:500]).strip()}"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except FileNotFoundError as e:
        return False, f"not_found: {e}"
    except Exception as e:
        return False, str(e)[:200]


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="用 SWE-agent 跑 issue_pr_map 中的 issue，统计多少环境能跑",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python run_sweagent_env_check.py\n  python run_sweagent_env_check.py --limit 3 --out-dir ./sweagent_check",
    )
    parser.add_argument("--issue-pr-map", default=None, help="issue_pr_map.json 路径")
    parser.add_argument("--out-dir", type=Path, default=RQ2_DIR, help="结果输出目录")
    parser.add_argument("--env-file", type=Path, default=None, help=".env 或 .swefactory.env 路径（可选）")
    parser.add_argument("--limit", type=int, default=None, help="只跑前 N 条（测试用）")
    parser.add_argument("--cost-limit", type=float, default=0.5, help="每个 instance 成本上限（美元）")
    parser.add_argument("--timeout", type=int, default=600, help="每个 instance 超时秒数")
    parser.add_argument("--config", type=Path, default=SWEAGENT_CONFIG, help="SWE-agent config.yaml")
    args = parser.parse_args()

    # 加载 API 环境
    env = {}
    if args.env_file and args.env_file.is_file():
        env = _load_export_env(args.env_file)
    else:
        for p in ENV_FILES:
            if p.is_file():
                env = _load_export_env(p)
                break
    import os
    if not env.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        print("Error: 未设置 OPENAI_API_KEY（请放在 .swefactory.env 或环境变量中）", file=sys.stderr)
        sys.exit(1)
    _apply_env_to_process(env)  # 合并到当前进程，便于子进程继承

    # 加载 issue 列表
    map_path = Path(args.issue_pr_map or ISSUE_PR_MAP_PATH)
    if not map_path.exists():
        print(f"Error: issue_pr_map 不存在: {map_path}", file=sys.stderr)
        sys.exit(1)
    items = load_issue_pr_map(map_path)
    if args.limit is not None:
        items = items[: args.limit]
    if not items:
        print("No issues to run.", file=sys.stderr)
        sys.exit(0)

    if not args.config.exists():
        print(f"Error: SWE-agent config 不存在: {args.config}", file=sys.stderr)
        sys.exit(1)

    # 输出目录
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.out_dir / "sweagent_env_check" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, rec in enumerate(items):
        repo = rec.get("repo", "")
        issue_num = rec.get("issue_number")
        key = issue_key(rec)
        print(f"[{i+1}/{len(items)}] {key} ... ", end="", flush=True)
        ok, msg = run_sweagent_once(
            repo,
            issue_num,
            env,
            config_path=args.config,
            cost_limit=args.cost_limit,
            timeout_sec=args.timeout,
        )
        results.append({"key": key, "repo": repo, "issue_number": issue_num, "ok": ok, "message": msg})
        print("ok" if ok else f"fail: {msg[:80]}", flush=True)

    # 写结果
    result_path = run_dir / "results.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    n_ok = sum(1 for r in results if r["ok"])
    summary_path = run_dir / "summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"total={len(results)}\nok={n_ok}\nfail={len(results)-n_ok}\n")
        for r in results:
            f.write(f"  {r['key']}: {'ok' if r['ok'] else r['message']}\n")

    print()
    print("=" * 60)
    print(f"  环境能跑: {n_ok}/{len(results)}")
    print(f"  结果目录: {run_dir}")
    print("=" * 60)
    return 0 if n_ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
