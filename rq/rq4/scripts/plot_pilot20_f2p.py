#!/usr/bin/env python3
"""Plot cumulative f2p rate vs #issues processed, one line per (combo, skill).

Reads ``results/rq4/all_combos_scores.csv`` and writes
``results/rq4/figures/pilot20_cumulative_f2p.png`` plus a PDF copy.

X-axis = # issues processed (0..N for that combo/skill)
Y-axis = cumulative f2p count (NOT rate, since the rate is meaningless
        when all pass@1 = 0%; the count is more informative)
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path("results/rq4")
CSV = RESULTS / "all_combos_scores.csv"
OUT_PNG = RESULTS / "figures/pilot20_cumulative_f2p.png"
OUT_PDF = RESULTS / "figures/pilot20_cumulative_f2p.pdf"


def load_rows():
    with CSV.open() as f:
        return list(csv.DictReader(f))


def main():
    rows = load_rows()
    # Group by (combo, skill_mode)
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[(r["combo"], r["skill_mode"])].append(r)

    # Order issues by appearance to make a meaningful "cumulative" curve
    # (we just iterate in file order since each row is a unique (issue, skill))
    fig, ax = plt.subplots(figsize=(9, 5))

    palette = {
        ("mini-swe-agent_40", "with"): "#1f77b4",
        ("mini-swe-agent_40", "without"): "#1f77b4",
        ("mini-swe-agent_60", "with"): "#2ca02c",
        ("mini-swe-agent_60", "without"): "#2ca02c",
        ("mini-swe-agent_80", "with"): "#d62728",
        ("mini-swe-agent_80", "without"): "#d62728",
        ("openhands_40", "with"): "#9467bd",
        ("openhands_40", "without"): "#9467bd",
        ("openhands_60", "with"): "#8c564b",
        ("openhands_60", "without"): "#8c564b",
        ("openhands_80", "with"): "#e377c2",
        ("openhands_80", "without"): "#e377c2",
    }
    linestyle = {"with": "-", "without": "--"}

    legend_handles = []
    # Sort by combo first then skill
    for (combo, skill) in sorted(by_cell.keys()):
        cell_rows = by_cell[(combo, skill)]
        # Build cumulative f2p
        cum = []
        n = 0
        f2p_n = 0
        for r in cell_rows:
            n += 1
            if r["outcome"] == "f2p":
                f2p_n += 1
            cum.append((n, f2p_n))
        xs = [c[0] for c in cum]
        ys = [c[1] for c in cum]

        label = f"{combo} ({'with' if skill=='with' else 'no'}-skill)"
        (line,) = ax.plot(
            xs,
            ys,
            color=palette[(combo, skill)],
            linestyle=linestyle[skill],
            linewidth=1.5,
            marker="o",
            markersize=3,
            label=label,
        )
        legend_handles.append(line)

    ax.set_xlabel("# issues processed")
    ax.set_ylabel("cumulative f2p count")
    ax.set_title("Cumulative f2p across pilot-20 (6 combos × 2 skill modes)")
    ax.set_xlim(0, max(len(v) for v in by_cell.values()) + 1)
    max_f2p = max(sum(1 for r in v if r["outcome"] == "f2p") for v in by_cell.values())
    ax.set_ylim(-0.1, max(1, max_f2p) + 0.5)
    ax.grid(True, linestyle=":", alpha=0.4)
    ax.legend(loc="upper left", fontsize=8, ncol=2)

    # Annotate pass@1 = 0% in the title corner
    ax.text(
        0.99,
        0.99,
        "pass@1 = 0% across all cells\n(agent-produced patches are malformed)",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.8),
    )

    fig.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=160)
    fig.savefig(OUT_PDF)
    print(f"Wrote {OUT_PNG}")
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
