#!/usr/bin/env python3
"""Plot per-combo outcome bars: f2p / f2f / error / no_patch.

Reads ``results/rq4/all_combos_scores.csv`` and writes
``results/rq4/figures/pilot20_outcome_breakdown.png`` (PDF copy too).

Bars are split by (combo, skill_mode) — 12 cells in two rows (one per skill).
"""

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS = Path("results/rq4")
CSV = RESULTS / "all_combos_scores.csv"
OUT_PNG = RESULTS / "figures/pilot20_outcome_breakdown.png"
OUT_PDF = RESULTS / "figures/pilot20_outcome_breakdown.pdf"


def main():
    cells = defaultdict(Counter)
    with CSV.open() as f:
        r = csv.DictReader(f)
        for row in r:
            cells[(row["combo"], row["skill_mode"])][row["outcome"] or "no_patch"] += 1

    combos = [
        "mini-swe-agent_40",
        "mini-swe-agent_60",
        "mini-swe-agent_80",
        "openhands_40",
        "openhands_60",
        "openhands_80",
    ]
    skill_modes = ["with", "without"]
    categories = ["f2p", "f2f", "error", "no_patch"]
    colors = {
        "f2p": "#2ca02c",
        "f2f": "#9467bd",
        "error": "#d62728",
        "no_patch": "#7f7f7f",
    }

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, skill in zip(axes, skill_modes):
        x = np.arange(len(combos))
        bottoms = np.zeros(len(combos))
        for cat in categories:
            vals = np.array([cells[(c, skill)][cat] for c in combos])
            ax.bar(
                x,
                vals,
                bottom=bottoms,
                color=colors[cat],
                label=cat,
                edgecolor="white",
                linewidth=0.6,
            )
            for i, v in enumerate(vals):
                if v > 0:
                    ax.text(
                        x[i],
                        bottoms[i] + v / 2,
                        str(int(v)),
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                    )
            bottoms += vals
        ax.set_xticks(x)
        ax.set_xticklabels([c.replace("mini-swe-agent", "mini") for c in combos], rotation=30, ha="right")
        ax.set_title(f"{skill}-skill")
        ax.set_ylabel("# rollouts (out of 20)")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        ax.set_axisbelow(True)
    axes[0].legend(loc="upper right", fontsize=9)

    fig.suptitle("Per-combo outcome breakdown (6 combos × 20 issues each)", fontsize=11)
    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=160)
    fig.savefig(OUT_PDF)
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
