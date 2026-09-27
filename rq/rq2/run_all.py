#!/usr/bin/env python3
"""
RQ2 一键运行：依次执行三种方法（rule_based → forge_ai → claude_agent）。
可选 --stability-runs N：每种方法跑 N 次，并计算两种稳定性（S_set 交并比、S_entropy 熵稳定性）。
"""

import json
import math
import subprocess
import sys
from pathlib import Path

_RQ2_DIR = Path(__file__).resolve().parent
_ISSUE_PR_MAP = _RQ2_DIR / "issue_pr_map.json"

METHODS = [
    ("rule_based", "rule_based/run_rule_based.py", "rule_based", "规则/启发式"),
    ("forge_ai", "forge_ai/run_forge_ai.py", "forge", "裸 AI (Forge)"),
    ("claude_agent", "claude_agent/run_claude_agent.py", "claude", "Claude Agent"),
]


def _load_issue_pr_map(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _issue_key(rec: dict) -> str:
    repo = (rec.get("repo") or "").replace("/", "-")
    return f"{repo}-{rec.get('issue_number', '')}"


def _collect_latest_run_dirs(base: Path, result_subdir: str, n: int) -> list:
    """在 base 下找最新 n 个时间戳目录，每个时间戳下要有 result_subdir 且含 *.txt。"""
    if not base.exists():
        return []
    candidates = []
    for d in base.iterdir():
        if not d.is_dir() or not d.name.replace("_", "").isdigit():
            continue
        method_dir = d / result_subdir
        if method_dir.exists() and any(method_dir.glob("*.txt")):
            candidates.append((d.name, method_dir))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[1] for c in candidates[:n]]


def _read_run_results(result_dir: Path, items: list) -> dict:
    """读单次运行结果：issue_key -> "yes"|"no"（只取 txt 第一行）。"""
    out = {}
    for rec in items:
        key = _issue_key(rec)
        fpath = result_dir / f"{key}.txt"
        if not fpath.exists():
            out[key] = "no"
            continue
        try:
            first_line = (fpath.read_text(encoding="utf-8").split("\n")[0] or "").strip().lower()
            out[key] = "yes" if first_line == "yes" else "no"
        except Exception:
            out[key] = "no"
    return out


def _s_set(run_results: list) -> float:
    """S_set = |A_∩| / |A_∪|，A_i = 第 i 次运行中判为 agent 的 issue 集合。"""
    if not run_results:
        return 1.0
    a_intersection = None
    a_union = set()
    for run in run_results:
        a_i = {k for k, v in run.items() if v == "yes"}
        a_union |= a_i
        if a_intersection is None:
            a_intersection = set(a_i)
        else:
            a_intersection &= a_i
    if not a_union:
        return 1.0
    return len(a_intersection) / len(a_union)


def _s_entropy(run_results: list, issue_keys: list) -> float:
    """S_entropy = 1 - H̄，H_j = -p_j*log2(p_j)-(1-p_j)*log2(1-p_j)，p_j = f_j/m。"""
    if not run_results or not issue_keys:
        return 1.0
    m = len(run_results)
    n = len(issue_keys)
    total_h = 0.0
    for key in issue_keys:
        f_j = sum(1 for run in run_results if run.get(key) == "yes")
        p_j = f_j / m
        if p_j <= 0 or p_j >= 1:
            h_j = 0.0
        else:
            h_j = -p_j * math.log2(p_j) - (1 - p_j) * math.log2(1 - p_j)
        total_h += h_j
    h_bar = total_h / n
    return 1.0 - h_bar


def _accuracy(run_result: dict) -> float:
    """单次准确率（假设均为 agent issue）：预测 yes 的比例。多轮时取各轮准确率的平均，故平均准确率不必为 0.05 的倍数。"""
    if not run_result:
        return 0.0
    n_yes = sum(1 for v in run_result.values() if v == "yes")
    return n_yes / len(run_result)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="RQ2: 依次运行三种方法，可选多次实验计算稳定性 (S_set, S_entropy)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python run_all.py\n  python run_all.py --stability-runs 5\n  python run_all.py --limit 5 --stability-runs 3",
    )
    parser.add_argument("--issue-pr-map", default=None, help="issue_pr_map.json 路径（默认: 本目录下）")
    parser.add_argument("--token", default=None, help="GitHub token（或设 GITHUB_TOKEN）")
    parser.add_argument("--limit", type=int, default=None, help="只处理前 N 条（用于快速测试）")
    parser.add_argument("--stability-runs", type=int, default=0, help="每种方法跑 N 次并计算 S_set、S_entropy（建议 3~5）")
    args = parser.parse_args()

    issue_pr_map_path = Path(args.issue_pr_map or str(_ISSUE_PR_MAP))
    if not issue_pr_map_path.exists():
        print(f"Error: issue_pr_map 不存在: {issue_pr_map_path}", file=sys.stderr)
        sys.exit(1)

    items = _load_issue_pr_map(issue_pr_map_path)
    if args.limit is not None:
        items = items[: args.limit]
    issue_keys = [_issue_key(r) for r in items]

    n_runs = max(0, args.stability_runs)
    if n_runs >= 2:
        # 多次实验：每种方法跑 n_runs 次，再算稳定性
        for subdir, script_rel, result_subdir, name in METHODS:
            script_path = _RQ2_DIR / script_rel
            if not script_path.exists():
                print(f"Skip: {script_path} 不存在", file=sys.stderr)
                continue
            base_out = _RQ2_DIR / subdir
            print("\n" + "=" * 60, file=sys.stderr)
            print(f"  [RQ2] {name}: 跑 {n_runs} 次实验", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            for r in range(n_runs):
                cmd = [
                    sys.executable,
                    str(script_path),
                    "--issue-pr-map", str(issue_pr_map_path),
                    "--out-dir", str(base_out),
                ]
                if args.token:
                    cmd += ["--token", args.token]
                if args.limit is not None:
                    cmd += ["--limit", str(args.limit)]
                print(f"  Run {r+1}/{n_runs} ...", file=sys.stderr)
                subprocess.run(cmd, cwd=str(script_path.parent))

            run_dirs = _collect_latest_run_dirs(base_out, result_subdir, n_runs)
            if len(run_dirs) < n_runs:
                print(f"  Warning: 只找到 {len(run_dirs)} 次运行结果，需要 {n_runs} 次", file=sys.stderr)
            run_results = [_read_run_results(d, items) for d in run_dirs[:n_runs]]
            if run_results:
                s_set = _s_set(run_results)
                s_entropy = _s_entropy(run_results, issue_keys)
                # 平均准确率：最近 n_runs 次运行各自准确率的平均（假设 20 条均为 agent issue）
                acc = sum(_accuracy(r) for r in run_results) / len(run_results)
                print(f"\n  [{name}] S_set = {s_set:.4f}  |  S_entropy = {s_entropy:.4f}  |  Accuracy = {acc:.4f}\n", file=sys.stderr)
                # 写一份稳定性结果到该方法目录下
                report_path = base_out / "stability_report.txt"
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"method={name}\nstability_runs={len(run_results)}\nS_set={s_set:.6f}\nS_entropy={s_entropy:.6f}\naccuracy={acc:.6f}\n")
                print(f"  已写入: {report_path}", file=sys.stderr)
    else:
        # 原逻辑：每种方法跑一次
        for subdir, script_rel, result_subdir, name in METHODS:
            script_path = _RQ2_DIR / script_rel
            if not script_path.exists():
                print(f"Skip: {script_path} 不存在", file=sys.stderr)
                continue
            base_out = _RQ2_DIR / subdir
            cmd = [
                sys.executable,
                str(script_path),
                "--issue-pr-map", str(issue_pr_map_path),
                "--out-dir", str(base_out),
            ]
            if args.token:
                cmd += ["--token", args.token]
            if args.limit is not None:
                cmd += ["--limit", str(args.limit)]

            print("\n" + "=" * 60, file=sys.stderr)
            print(f"  [RQ2] {name}: {script_rel}", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            ret = subprocess.run(cmd, cwd=str(script_path.parent))
            if ret.returncode != 0:
                print(f"  Warning: {script_rel} 退出码 {ret.returncode}", file=sys.stderr)
            # 单次运行也计算并写入准确率（假设均为 agent issue）
            run_dirs = _collect_latest_run_dirs(base_out, result_subdir, 1)
            if run_dirs:
                single_result = _read_run_results(run_dirs[0], items)
                acc = _accuracy(single_result)
                report_path = base_out / "stability_report.txt"
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(f"method={name}\naccuracy={acc:.6f}\n")
                print(f"  [{name}] Accuracy = {acc:.4f}  (假设均为 agent issue)", file=sys.stderr)

    print("\n" + "=" * 60, file=sys.stderr)
    print("  RQ2 执行完毕", file=sys.stderr)
    print("=" * 60 + "\n", file=sys.stderr)


if __name__ == "__main__":
    main()
