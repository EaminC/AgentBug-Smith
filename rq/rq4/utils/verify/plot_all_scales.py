#!/usr/bin/env python3
"""Plot cumulative pass@1 for all 12 (agent, scale, skill) combos.

Usage:
    python utils/verify/plot_all_scales.py --csv results/rq4/all_scales_scores.csv
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── style maps ────────────────────────────────────────────────────────────────
AGENT_COLOR   = {"mini-swe-agent": "#2980b9", "openhands": "#c0392b"}
SCALE_LS     = {40: "-",  60: "--", 80: "-."}
SCALE_MARKER  = {40: "o",  60: "s",  80: "^"}
SKILL_LW     = {"with": 2.0, "without": 1.2}
SKILL_ALPHA  = {"with": 0.90, "without": 0.55}


def load(csv_path: Path):
    rows_by_key = {}
    for r in csv.DictReader(csv_path.open(newline="")):
        key = (r["agent"], int(r["train_size"]), r["skill_mode"])
        rows_by_key.setdefault(key, []).append(r)
    # sort each group by issue index
    def idx(row):
        return int(row["issue"].split("-")[1])
    for v in rows_by_key.values():
        v.sort(key=idx)
    return rows_by_key


def cum_pass1(rows):
    """Return (x, y_cum, y_lo, y_hi) for cumulative f2p."""
    k = 0
    xs, ys, los, his = [], [], [], []
    for i, r in enumerate(rows, 1):
        if r["outcome"] == "f2p":
            k += 1
        rate = k / i
        z = 1.96
        denom = 1 + z**2 / i
        center = (rate + z**2 / (2 * i)) / denom
        margin = z * np.sqrt(rate * (1 - rate) / i + z**2 / (4 * i**2)) / denom
        xs.append(i)
        ys.append(rate)
        los.append(max(0, center - margin))
        his.append(min(1, center + margin))
    return xs, ys, los, his


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path,
                    default=REPO_ROOT / "results" / "rq4" / "all_scales_scores.csv")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "results" / "rq4" / "figures" / "all_scales_cumulative.png")
    args = ap.parse_args()

    data = load(args.csv)
    out_dir = args.out.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Fig 1: cumulative curves ─────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(13, 7))

    for (agent, scale, skill), rows in sorted(data.items()):
        xs, ys, los, his = cum_pass1(rows)
        c  = AGENT_COLOR.get(agent, "#555")
        ls = SCALE_LS.get(scale, "-")
        mk = SCALE_MARKER.get(scale, "o")
        lw = SKILL_LW.get(skill, 1.5)
        al = SKILL_ALPHA.get(skill, 0.7)
        label = f"{agent[:4]} s{scale} {skill}"
        ax.plot(xs, [y*100 for y in ys], color=c, linestyle=ls, marker=mk,
                linewidth=lw, alpha=al, label=label, markersize=7, zorder=3)
        ax.fill_between(xs, [lo*100 for lo in los], [hi*100 for hi in his],
                       color=c, alpha=0.08, zorder=2)

    ax.set_xlabel("issue index (1 → 20)", fontsize=12)
    ax.set_ylabel("cumulative f2p rate (%)", fontsize=12)
    ax.set_title("Cumulative pass@1 across 20 issues\n"
                 "12 methods: 2 agents × 3 scales (40/60/80) × with/without skill",
                 fontsize=13)
    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(-3, 65)
    ax.set_xticks(range(1, 21))
    ax.grid(True, alpha=0.3, zorder=1)

    # legend
    from matplotlib.lines import Line2D
    handles = []
    for agent, color in AGENT_COLOR.items():
        handles.append(Line2D([0], [0], color=color, linewidth=2.5,
                               label=agent))
    for scale, ls in SCALE_LS.items():
        handles.append(Line2D([0], [0], color="gray", linewidth=2,
                               linestyle=ls, marker=SCALE_MARKER[scale],
                               label=f"scale={scale}"))
    for skill in ("with", "without"):
        handles.append(mpatches.Patch(
            alpha=SKILL_ALPHA[skill], color="gray", label=skill))
    ax.legend(handles=handles, fontsize=9, framealpha=0.95,
              loc="upper right", ncol=2)
    plt.tight_layout()
    fig.savefig(args.out, dpi=150)
    plt.close(fig)
    print(f"wrote {args.out}")

    # ── Fig 2: final pass@1 bar chart ─────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    keys = sorted(data.keys())
    labels = [f"{a[:4]} s{s} {sk}" for a, s, sk in keys]
    rates = []
    for k in keys:
        rows = data[k]
        n = len(rows)
        f2p = sum(1 for r in rows if r["outcome"] == "f2p")
        rates.append(100 * f2p / max(n, 1))

    colors = [AGENT_COLOR[k[0]] for k in keys]
    alphas = [SKILL_ALPHA[k[2]] for k in keys]
    bars = ax2.bar(labels, rates, color=colors, alpha=0.85,
                   edgecolor="white", linewidth=1)
    for bar, (k, rate) in zip(bars, zip(keys, rates)):
        bar.set_alpha(SKILL_ALPHA[k[2]])
        if rate > 0:
            ax2.text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 1,
                     f"{rate:.1f}%", ha="center", va="bottom",
                     fontsize=9, fontweight="bold")
    ax2.set_ylabel("final f2p rate (%)", fontsize=12)
    ax2.set_title("Final pass@1 after 20 issues\n(2 agents × 3 scales × 2 skill modes)",
                  fontsize=13)
    ax2.set_ylim(0, 40)
    ax2.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=25, ha="right", fontsize=9)
    plt.tight_layout()
    out2 = out_dir / "all_scales_final_bars.png"
    fig2.savefig(out2, dpi=150)
    plt.close(fig2)
    print(f"wrote {out2}")

    # ── Print table ───────────────────────────────────────────────────────
    print(f"\n{'agent':16s} {'scale':6s} {'skill':8s} {'n':>4s} "
          f"{'f2p':>4s} {'f2f':>4s} {'p2p':>4s} {'pass@1':>7s}")
    for k in keys:
        rows = data[k]
        n = len(rows)
        from collections import Counter
        c = Counter(r["outcome"] for r in rows)
        f2p = c.get("f2p", 0)
        f2f = c.get("f2f", 0)
        p2p = c.get("p2p", 0)
        print(f"{k[0]:16s} s{k[1]:4d} {k[2]:8s} {n:4d} "
              f"{f2p:4d} {f2f:4d} {p2p:4d} {100*f2p/max(n,1):6.1f}%")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
