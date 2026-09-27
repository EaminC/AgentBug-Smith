#!/usr/bin/env python3
"""Plot cumulative pass@1 rate over 20 issues for each (agent, skill) combo.

X-axis = issue index 0..20, Y-axis = cumulative f2p rate.
Non-buildable issues are shown as 0 (they can't be fixed).

Usage:
    python utils/verify/plot_pilot20.py
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH  = REPO_ROOT / "results" / "rq4" / "pilot_20_scores.csv"
OUT_DIR   = REPO_ROOT / "results" / "rq4" / "figures"

# ── style ────────────────────────────────────────────────────────────────────
COLORS  = {"mini-swe-agent": "#2980b9", "openhands": "#c0392b"}
MARKERS = {"with": "o", "without": "s"}
STYLES  = {"with": "-",    "without": "--"}
LABELS  = {
    ("mini-swe-agent", "with"):    "mini-swe + skill",
    ("mini-swe-agent", "without"): "mini-swe (no skill)",
    ("openhands",     "with"):    "OH + skill",
    ("openhands",     "without"): "OH (no skill)",
}


def load_combos():
    """Return dict: (agent, skill) → list of rows, sorted by issue index."""
    combos = defaultdict(list)
    for r in csv.DictReader(CSV_PATH.open()):
        combos[(r["agent"], r["skill_mode"])].append(r)

    def issue_idx(r):
        # e.g. "issue-1077" → 1077
        return int(r["issue"].split("-")[1])

    for rows in combos.values():
        rows.sort(key=issue_idx)
    return combos


def main() -> int:
    combos = load_combos()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Fig 1: cumulative pass@1 0..20 ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 6))

    for (agent, skill), rows in sorted(combos.items()):
        n = len(rows)
        x_all   = list(range(1, n + 1))
        y_cum   = []
        y_lower = []
        y_upper = []

        f2p_count = 0
        for i, r in enumerate(rows, 1):
            if r["outcome"] == "f2p":
                f2p_count += 1
            rate = f2p_count / i
            y_cum.append(rate)

            # Wilson 95% CI
            z = 1.96
            denom = 1 + z**2 / i
            center = (rate + z**2 / (2 * i)) / denom
            margin = z * np.sqrt(rate * (1 - rate) / i + z**2 / (4 * i**2)) / denom
            y_lower.append(max(0, center - margin))
            y_upper.append(min(1, center + margin))

        c  = COLORS.get(agent, "#555")
        ls = STYLES.get(skill, "-")
        mk = MARKERS.get(skill, "o")
        label = LABELS.get((agent, skill), f"{agent} {skill}")

        ax.plot(x_all, [v * 100 for v in y_cum],
                marker=mk, linestyle=ls, color=c,
                label=label, linewidth=2.5, markersize=7, zorder=3)
        ax.fill_between(x_all,
                        [lo * 100 for lo in y_lower],
                        [hi * 100 for hi in y_upper],
                        color=c, alpha=0.12, zorder=2)

        # Mark buildable vs non-buildable with different opacities
        for i, r in enumerate(rows, 1):
            color = "green" if r["has_patch"] == "True" else "gray"
            ax.scatter([i], [y_cum[-1] * 100],
                       color=color, s=30 if r["has_patch"] == "True" else 10,
                       zorder=4)

    ax.set_xlabel("issue index (1 → 20)", fontsize=12)
    ax.set_ylabel("cumulative f2p rate (%)", fontsize=12)
    ax.set_title("Cumulative pass@1 across 20 issues\n"
                 "4 methods: mini-swe-agent × openhands × with/without skill",
                 fontsize=13)
    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(-3, 65)
    ax.set_xticks(range(1, 21))
    ax.grid(True, alpha=0.3, zorder=1)

    # Legend: style + buildable marker
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=COLORS["mini-swe-agent"], linewidth=2.5,
               linestyle="-",  marker="o", label="mini-swe + skill"),
        Line2D([0], [0], color=COLORS["mini-swe-agent"], linewidth=2.5,
               linestyle="--", marker="s", label="mini-swe (no skill)"),
        Line2D([0], [0], color=COLORS["openhands"],      linewidth=2.5,
               linestyle="-",  marker="o", label="OH + skill"),
        Line2D([0], [0], color=COLORS["openhands"],      linewidth=2.5,
               linestyle="--", marker="s", label="OH (no skill)"),
        Line2D([0], [0], marker="o", color="gray", markersize=8,
               linestyle="none", label="buildable (has patch)"),
        mpatches.Patch(color="gray", alpha=0.5, label="non-buildable"),
    ]
    ax.legend(handles=legend_elements, fontsize=10, framealpha=0.95,
              loc="upper right")
    plt.tight_layout()

    out1 = OUT_DIR / "pilot20_cumulative_pass1.png"
    fig.savefig(out1, dpi=150)
    plt.close(fig)
    print(f"wrote {out1}")

    # ── Fig 2: final bar chart ─────────────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    keys = sorted(combos.keys())
    final_rates = []
    for (agent, skill), rows in sorted(combos.items()):
        f2p = sum(1 for r in rows if r["outcome"] == "f2p")
        buildable = sum(1 for r in rows if r["has_patch"] == "True")
        rate = f2p / len(rows) * 100
        final_rates.append(rate)

    bars = ax2.bar(
        [LABELS[k] for k in keys],
        final_rates,
        color=[COLORS[k[0]] for k in keys],
        edgecolor="white", linewidth=1.5,
    )
    for bar, (k, rate) in zip(bars, zip(keys, final_rates)):
        bar.set_alpha(0.85 if k[1] == "with" else 0.55)
    for bar, rate in zip(bars, final_rates):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 1.5,
                 f"{rate:.1f}%",
                 ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax2.set_ylabel("cumulative f2p rate (%)", fontsize=12)
    ax2.set_title("Final pass@1 after 20 issues\n(f2p / 20)", fontsize=13)
    ax2.set_ylim(0, 35)
    ax2.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=15, ha="right", fontsize=10)
    plt.tight_layout()

    out2 = OUT_DIR / "pilot20_final_bars.png"
    fig2.savefig(out2, dpi=150)
    plt.close(fig2)
    print(f"wrote {out2}")

    # ── Print summary ──────────────────────────────────────────────────────
    print("\n=== Final summary ===")
    for (agent, skill), rows in sorted(combos.items()):
        f2p      = sum(1 for r in rows if r["outcome"] == "f2p")
        buildable= sum(1 for r in rows if r["has_patch"] == "True")
        print(f"  {agent} {skill}_skill: {f2p}/{len(rows)} f2p  "
              f"({100*f2p/len(rows):.1f}%),  buildable={buildable}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
