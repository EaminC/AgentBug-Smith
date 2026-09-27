"""Visualize split-stage results.

Reads ``results/split/sweep.jsonl`` and ``results/split/distribution.json``
and emits PNG figures + a ``README.md`` index into ``results/split/figures/``.

Figures produced (one per strategy where applicable):

1. ``01_per_repo_counts.png`` — bar chart of issues per repo.
2. ``02_per_category_counts.png`` — bar chart of issues per category.
3. ``03_category_x_repo_heatmap.png`` — category × repo heatmap.
4. ``04_train_size_vs_actual.png`` — req vs actual train size, all 3
   strategies on one plot.
5. ``05_leakage_vs_train_size.png`` — req vs leakage %, all 3 strategies.
6. ``06_cats_coverage_vs_train_size.png`` — req vs categories covered.
7. ``07_strategy_comparison.png`` — small-multiple bar chart of the
   side-by-side averages.
8. ``08_repo_size_distribution.png`` — histogram of repo sizes with
   mean/median markers.

Usage::

    python utils/split/visualize.py
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_sweep(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_dist(path: Path) -> dict:
    return json.loads(path.read_text())


def avg_by(rows: list[dict], key: tuple[str, str], value: str
           ) -> dict[tuple[str, int], float]:
    """For each (mode, train_size_requested), average ``value`` over
    the repeats."""
    bucket: dict[tuple[str, int], list[float]] = {}
    for r in rows:
        bucket.setdefault((r[key[0]], r[key[1]]), []).append(r[value])
    return {k: sum(v) / len(v) for k, v in bucket.items()}


def cats_covered_avg(rows: list[dict]) -> dict[tuple[str, int], float]:
    bucket: dict[tuple[str, int], list[float]] = {}
    for r in rows:
        cats = r["train_category_counts"]
        cov = sum(1 for c in "ABCDEF" if c in cats) / 6
        bucket.setdefault((r["mode"], r["train_size_requested"]), []).append(cov)
    return {k: sum(v) / len(v) for k, v in bucket.items()}


def fig_per_repo(distribution: dict, out: Path) -> None:
    repos = distribution["repo_counts"]
    names = list(repos.keys())
    counts = list(repos.values())
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(range(len(names)), counts, color="#4c72b0")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("# issues")
    ax.set_title("Per-repo issue count (n=200, 11 repos)")
    for i, v in enumerate(counts):
        ax.text(i, v + 1, str(v), ha="center", fontsize=8)
    ax.set_ylim(0, max(counts) * 1.15)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_per_category(distribution: dict, out: Path) -> None:
    cats = distribution["category_counts"]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(list(cats.keys()), list(cats.values()),
                  color=["#dd8452", "#55a868", "#c44e52", "#8172b3",
                         "#937860", "#da8bc3"])
    ax.set_ylabel("# issues")
    ax.set_xlabel("category")
    ax.set_title("Per-category issue count")
    for b, v in zip(bars, cats.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, str(v),
                ha="center", fontsize=9)
    ax.set_ylim(0, max(cats.values()) * 1.18)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_heatmap(distribution: dict, out: Path) -> None:
    cross = distribution["category_x_repo"]
    cats = sorted(cross)
    repos = sorted({r for c in cats for r in cross[c]},
                   key=lambda r: -distribution["repo_counts"][r])
    matrix = np.array([[cross[c].get(r, 0) for r in repos] for c in cats])
    fig, ax = plt.subplots(figsize=(11, 4.5))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(repos)))
    ax.set_xticklabels(repos, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(cats)))
    ax.set_yticklabels(cats)
    ax.set_xlabel("repo")
    ax.set_ylabel("category")
    ax.set_title("Category × repo cross-tab (# issues)")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            v = matrix[i, j]
            color = "white" if v > matrix.max() * 0.6 else "black"
            ax.text(j, i, str(v), ha="center", va="center",
                    color=color, fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_repo_size_hist(distribution: dict, out: Path) -> None:
    sizes = list(distribution["repo_counts"].values())
    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.arange(min(sizes), max(sizes) + 5, 5)
    ax.hist(sizes, bins=bins, color="#4c72b0", edgecolor="white")
    ax.axvline(np.mean(sizes), color="red", linestyle="--",
               label=f"mean={np.mean(sizes):.1f}")
    ax.axvline(np.median(sizes), color="orange", linestyle=":",
               label=f"median={np.median(sizes):.1f}")
    ax.set_xlabel("issues per repo")
    ax.set_ylabel("# repos")
    ax.set_title("Repo size distribution (n=11 repos)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_train_size_vs_actual(rows: list[dict], out: Path) -> None:
    reqs = sorted({r["train_size_requested"] for r in rows})
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"default": "#4c72b0", "repo_disjoint": "#dd8452",
              "greedy_issue": "#55a868"}
    labels = {"default": "A — bounded cap",
              "repo_disjoint": "B — repo_disjoint",
              "greedy_issue": "C — greedy_issue"}
    for mode in ("default", "repo_disjoint", "greedy_issue"):
        avg = avg_by(rows, ("mode", "train_size_requested"), "train_size")
        ys = [avg.get((mode, r), np.nan) for r in reqs]
        ax.plot(reqs, ys, marker="o", color=colors[mode],
                label=labels[mode], linewidth=2)
    ax.plot(reqs, reqs, linestyle="--", color="gray", alpha=0.6,
            label="y = x (perfect match)")
    ax.set_xlabel("requested train_size")
    ax.set_ylabel("actual train_size (mean over 3 repeats)")
    ax.set_title("Train size: requested vs actual (3 strategies)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_leakage(rows: list[dict], out: Path) -> None:
    reqs = sorted({r["train_size_requested"] for r in rows})
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"default": "#4c72b0", "repo_disjoint": "#dd8452",
              "greedy_issue": "#55a868"}
    labels = {"default": "A — bounded cap",
              "repo_disjoint": "B — repo_disjoint",
              "greedy_issue": "C — greedy_issue"}
    for mode in ("default", "repo_disjoint", "greedy_issue"):
        avg = avg_by(rows, ("mode", "train_size_requested"),
                     "test_repo_leakage_pct")
        ys = [avg.get((mode, r), np.nan) for r in reqs]
        ax.plot(reqs, ys, marker="o", color=colors[mode],
                label=labels[mode], linewidth=2)
    ax.set_xlabel("requested train_size")
    ax.set_ylabel("test_repo_leakage_pct (mean over 3 repeats)")
    ax.set_title("Repo leakage: % of test issues from a train repo")
    ax.set_ylim(-5, 110)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_cats_coverage(rows: list[dict], out: Path) -> None:
    reqs = sorted({r["train_size_requested"] for r in rows})
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"default": "#4c72b0", "repo_disjoint": "#dd8452",
              "greedy_issue": "#55a868"}
    labels = {"default": "A — bounded cap",
              "repo_disjoint": "B — repo_disjoint",
              "greedy_issue": "C — greedy_issue"}
    for mode in ("default", "repo_disjoint", "greedy_issue"):
        avg = cats_covered_avg(rows)
        ys = [avg.get((mode, r), np.nan) * 6 for r in reqs]
        ax.plot(reqs, ys, marker="o", color=colors[mode],
                label=labels[mode], linewidth=2)
    ax.set_xlabel("requested train_size")
    ax.set_ylabel("categories covered in train (out of 6)")
    ax.set_title("Category coverage across train_size × strategy")
    ax.set_ylim(0, 6.5)
    ax.set_yticks(range(0, 7))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def fig_comparison(rows: list[dict], out: Path) -> None:
    reqs = sorted({r["train_size_requested"] for r in rows})
    modes = ("default", "repo_disjoint", "greedy_issue")
    metrics = ("train_size", "test_repo_leakage_pct")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    x = np.arange(len(reqs))
    width = 0.25
    colors = {"default": "#4c72b0", "repo_disjoint": "#dd8452",
              "greedy_issue": "#55a868"}
    for ax, metric in zip(axes, metrics):
        for i, mode in enumerate(modes):
            avg = avg_by(rows, ("mode", "train_size_requested"), metric)
            ys = [avg.get((mode, r), 0) for r in reqs]
            ax.bar(x + (i - 1) * width, ys, width, label=mode,
                   color=colors[mode])
        ax.set_xticks(x)
        ax.set_xticklabels(reqs)
        ax.set_xlabel("requested train_size")
        if metric == "train_size":
            ax.set_ylabel("actual train_size")
            ax.plot(x, reqs, "k--", alpha=0.4, label="req line")
        else:
            ax.set_ylabel("leakage %")
        ax.set_title("Actual train size" if metric == "train_size"
                     else "Leakage %")
        ax.grid(alpha=0.3, axis="y")
        ax.legend(fontsize=8)
    fig.suptitle("Strategy comparison — averages over 3 repeats", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def write_index(fig_dir: Path) -> None:
    items = [
        ("01_per_repo_counts.png",
         "Per-repo issue counts (descending). Top repo holds ~40% of "
         "the corpus; 5 repos hold ≤ 5% each — strong skew."),
        ("02_per_category_counts.png",
         "Per-category issue counts. B is dominant, D is rare."),
        ("03_category_x_repo_heatmap.png",
         "Category × repo cross-tab heatmap. Shows which categories "
         "appear in which repos."),
        ("04_train_size_vs_actual.png",
         "Requested vs actual train_size for all three strategies."),
        ("05_leakage_vs_train_size.png",
         "Repo leakage % vs requested train_size for all three "
         "strategies."),
        ("06_cats_coverage_vs_train_size.png",
         "Number of A–F categories present in train, per strategy."),
        ("07_strategy_comparison.png",
         "Bar chart side-by-side: actual train_size and leakage for "
         "all three strategies."),
        ("08_repo_size_distribution.png",
         "Histogram of repo sizes with mean/median markers."),
    ]
    lines = ["# Figures\n",
             "All figures are generated by "
             "`utils/split/visualize.py` from "
             "`results/split/sweep.jsonl` and "
             "`results/split/distribution.json`.\n"]
    for fname, desc in items:
        lines.append(f"## `{fname}`\n")
        lines.append(f"![{fname}]({fname})\n")
        lines.append(f"{desc}\n")
    (fig_dir / "README.md").write_text("\n".join(lines) + "\n",
                                        encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep", type=Path,
                    default=Path("results/split/sweep.jsonl"))
    ap.add_argument("--distribution", type=Path,
                    default=Path("results/split/distribution.json"))
    ap.add_argument("--out", type=Path,
                    default=Path("results/split/figures"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    rows = load_sweep(args.sweep)
    dist = load_dist(args.distribution)

    fig_per_repo(dist, args.out / "01_per_repo_counts.png")
    fig_per_category(dist, args.out / "02_per_category_counts.png")
    fig_heatmap(dist, args.out / "03_category_x_repo_heatmap.png")
    fig_repo_size_hist(dist, args.out / "08_repo_size_distribution.png")
    fig_train_size_vs_actual(rows, args.out / "04_train_size_vs_actual.png")
    fig_leakage(rows, args.out / "05_leakage_vs_train_size.png")
    fig_cats_coverage(rows, args.out / "06_cats_coverage_vs_train_size.png")
    fig_comparison(rows, args.out / "07_strategy_comparison.png")
    write_index(args.out)
    print(f"Wrote 8 figures and README to {args.out}")


if __name__ == "__main__":
    main()
