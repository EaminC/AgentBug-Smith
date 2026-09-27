#!/usr/bin/env python3
"""plot_pilot30.py — render the pilot30 pass-rate figure.

Reads results/rq4/pilot30_scores.csv and renders a 6-facet
cumulative pass-rate plot (one facet per combo), with two lines
per facet: with_skill and without_skill.
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


SCORES = Path(__file__).resolve().parents[2] / "results/rq4/pilot30_scores.csv"
OUT_DIR = Path(__file__).resolve().parents[2] / "results/rq4/figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    rows = list(csv.DictReader(open(SCORES)))

    by_combo = defaultdict(list)
    for r in rows:
        by_combo[(r["agent"], r["scale"])].append(r)

    combos = sorted(by_combo.keys())
    n = len(combos)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), sharey=True)
    if n == 1:
        axes = [axes]

    for ax, (agent, scale) in zip(axes, combos):
        rs = by_combo[(agent, scale)]
        for skill, color in [("with_skill", "tab:blue"),
                             ("without_skill", "tab:orange")]:
            sub = [r for r in rs if r["skill"] == skill]
            # Sort by issue id for stable ordering
            sub.sort(key=lambda r: r["issue"])
            x = list(range(1, len(sub) + 1))
            y = []
            n_pass = 0
            for i, r in enumerate(sub, 1):
                if r["outcome"] == "f2p":
                    n_pass += 1
                y.append(100 * n_pass / i)
            if not y:
                y = [0]
            ax.plot(x, y, marker="o", color=color,
                    label=skill, linewidth=2.0)

        ax.set_title(f"{agent}_{scale}", fontsize=11)
        ax.set_xlabel("issue index")
        ax.set_ylim(-3, 60)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    axes[0].set_ylabel("cumulative pass@1 (%)")
    fig.suptitle("Pilot-30: cumulative pass@1 across 5 issues (with vs. without skill)",
                 fontsize=13)
    fig.tight_layout()

    out_path = OUT_DIR / "pilot30_cumulative_pass1.png"
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
