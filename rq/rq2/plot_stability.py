#!/usr/bin/env python3
"""绘制 RQ2 三种方法的 S_set / S_entropy 稳定性与平均准确率柱状图，第一项为 Ours (Rule hybrid)。
若 stability_report.txt 不完整，则从各方法目录下最近 N 次运行（与 run_all --stability-runs N 一致）重新计算。
"""

import json
import math
import re
from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

_RQ2_DIR = Path(__file__).resolve().parent
_OUT = _RQ2_DIR / "stability_figure.png"
_ISSUE_PR_MAP = _RQ2_DIR / "issue_pr_map.json"

# 与 run_all --stability-runs 5 一致：从最近 5 次试验计算
N_STABILITY_RUNS = 5

METHOD_NAMES = ["Ours\n(Rule hybrid)", "Forge", "Claude Agent"]
METHOD_SUBDIRS = ["rule_based", "forge_ai", "claude_agent"]
RESULT_SUBDIR = {"rule_based": "rule_based", "forge_ai": "forge", "claude_agent": "claude"}
DEFAULT_S_SET = [1.0000, 0.9412, 0.6111]
DEFAULT_S_ENTROPY = [1.0000, 0.9639, 0.7100]


def _issue_key(rec: dict) -> str:
    repo = (rec.get("repo") or "").replace("/", "-")
    return f"{repo}-{rec.get('issue_number', '')}"


def _load_items() -> list:
    if not _ISSUE_PR_MAP.exists():
        return []
    with open(_ISSUE_PR_MAP, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _collect_latest_run_dirs(base: Path, result_subdir: str, n: int) -> List[Path]:
    """在 base 下找最新 n 个时间戳目录（与 run_all 一致）。"""
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
    """读单次运行结果：issue_key -> "yes"|"no"（只取 txt 第一行，与 run_all 一致）。"""
    out = {}
    for rec in items:
        key = _issue_key(rec)
        fpath = result_dir / f"{key}.txt"
        if not fpath.exists():
            out[key] = "no"
            continue
        try:
            first = (fpath.read_text(encoding="utf-8").split("\n")[0] or "").strip().lower()
            out[key] = "yes" if first == "yes" else "no"
        except Exception:
            out[key] = "no"
    return out


def _s_set(run_results: List[dict]) -> float:
    """S_set = |A_∩| / |A_∪|（与 run_all 一致）。"""
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
    return len(a_intersection) / len(a_union) if a_union else 1.0


def _s_entropy(run_results: List[dict], issue_keys: list) -> float:
    """S_entropy = 1 - H̄（与 run_all 一致）。"""
    if not run_results or not issue_keys:
        return 1.0
    m, n = len(run_results), len(issue_keys)
    total_h = 0.0
    for key in issue_keys:
        f_j = sum(1 for run in run_results if run.get(key) == "yes")
        p_j = f_j / m
        if p_j <= 0 or p_j >= 1:
            h_j = 0.0
        else:
            h_j = -p_j * math.log2(p_j) - (1 - p_j) * math.log2(1 - p_j)
        total_h += h_j
    return 1.0 - (total_h / n)


def _accuracy(run_result: dict) -> float:
    """单次运行的准确率（假设均为 agent issue）：yes 数/总数。图表中的 Accuracy 为最近 5 次该值的平均。"""
    if not run_result:
        return 0.0
    n_yes = sum(1 for v in run_result.values() if v == "yes")
    return n_yes / len(run_result)


def _metrics_from_runs(subdir: str, items: list, issue_keys: list, n_runs: int) -> Optional[dict]:
    """从该方法最近 n_runs 次运行计算 S_set、S_entropy、accuracy（accuracy 为 n_runs 次准确率的平均）。"""
    base = _RQ2_DIR / subdir
    result_subdir_name = RESULT_SUBDIR.get(subdir)
    if not base.exists() or not result_subdir_name or not items:
        return None
    run_dirs = _collect_latest_run_dirs(base, result_subdir_name, n_runs)
    if len(run_dirs) < 2:
        return None
    run_results = [_read_run_results(d, items) for d in run_dirs[:n_runs]]
    acc_avg = sum(_accuracy(r) for r in run_results) / len(run_results)
    return {
        "S_set": _s_set(run_results),
        "S_entropy": _s_entropy(run_results, issue_keys),
        "accuracy": acc_avg,
    }


def _parse_report(report_path: Path) -> dict:
    out = {}
    if not report_path.exists():
        return out
    try:
        text = report_path.read_text(encoding="utf-8")
        for m in re.finditer(r"(?m)^(S_set|S_entropy|accuracy)=([\d.]+)", text):
            out[m.group(1)] = float(m.group(2))
    except Exception:
        pass
    return out


def _load_metrics():
    items = _load_items()
    issue_keys = [_issue_key(r) for r in items]
    s_set, s_entropy, accuracy = [], [], []
    for i, subdir in enumerate(METHOD_SUBDIRS):
        report = _parse_report(_RQ2_DIR / subdir / "stability_report.txt")
        # 若报告不完整，则从该目录最近 N_STABILITY_RUNS 次试验重新计算（与 run_all 一致）
        if report.get("S_set") is None or report.get("S_entropy") is None or report.get("accuracy") is None:
            from_runs = _metrics_from_runs(subdir, items, issue_keys, N_STABILITY_RUNS)
            if from_runs:
                report = {**report, **from_runs}
            elif report.get("accuracy") is None and items:
                # 不足 2 次运行无法算稳定性，至少用最近一次运行算准确率
                run_dirs = _collect_latest_run_dirs(_RQ2_DIR / subdir, RESULT_SUBDIR.get(subdir, ""), 1)
                if run_dirs:
                    single = _read_run_results(run_dirs[0], items)
                    report["accuracy"] = _accuracy(single)
        s_set.append(report.get("S_set", DEFAULT_S_SET[i]))
        s_entropy.append(report.get("S_entropy", DEFAULT_S_ENTROPY[i]))
        accuracy.append(report.get("accuracy", 0.0) if report.get("accuracy") is not None else 0.0)
    return s_set, s_entropy, accuracy


def main():
    s_set, s_entropy, accuracy = _load_metrics()
    methods = METHOD_NAMES
    x = np.arange(len(methods))
    width = 0.25

    fig, ax = plt.subplots(figsize=(7, 4))
    bars1 = ax.bar(x - width, s_set, width, label=r"$S_{\mathrm{set}}$", color="#2ecc71")
    bars2 = ax.bar(x, s_entropy, width, label=r"$S_{\mathrm{entropy}}$", color="#3498db")
    bars3 = ax.bar(x + width, accuracy, width, label="Accuracy", color="#e67e22")

    ax.set_ylabel("Score", fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=10)
    ax.legend(loc="lower left", fontsize=10)
    ax.set_ylim(0, 1.08)
    ax.set_title("Discriminator Stability & Accuracy for Agent-Issue Detection", fontsize=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for b in bars1:
        h = b.get_height()
        ax.annotate(f"{h:.2f}", xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#27ae60")
    for b in bars2:
        h = b.get_height()
        ax.annotate(f"{h:.2f}", xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#2980b9")
    for b in bars3:
        h = b.get_height()
        ax.annotate(f"{h:.2f}", xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, color="#d35400")

    plt.tight_layout()
    plt.savefig(_OUT, dpi=150, bbox_inches="tight")
    print(f"Saved: {_OUT}")
    plt.close()


if __name__ == "__main__":
    main()
