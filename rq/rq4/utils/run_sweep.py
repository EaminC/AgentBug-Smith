"""Sweep split/train-size combinations and report results.

For each (train_size, seed) pair, call ``utils.split.split`` and record:
- requested train_size
- actual train_size and test_size after the algorithm
- per-category counts in train
- test_repo_leakage_pct (the unavoidable cost on small datasets)
- train_unique_repos

Writes a JSONL ``results/sweep.jsonl`` and a human-readable
``results/sweep.md`` table.

Usage::

    python utils/run_sweep.py \
        --index data/index.jsonl \
        --train-sizes 20 40 60 80 100 120 140 160 180 \
        --repeats 3 \
        --out results
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make the split module importable as a library.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from split import run as split_mod  # type: ignore  # noqa: E402


def run_sweep(index: list[dict], train_sizes: list[int], repeats: int
              ) -> list[dict]:
    rows = []
    for ts in train_sizes:
        for rep in range(repeats):
            seed = 1000 * rep + ts  # deterministic per (ts, rep)
            for mode in ("default", "repo_disjoint", "greedy_issue"):
                _, _, summary = split_mod.split(index, ts, seed=seed,
                                                mode=mode)
                rows.append({
                    "mode": mode,
                    "train_size_requested": ts,
                    "repeat": rep,
                    "seed": seed,
                    **summary,
                })
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_markdown(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_total = rows[0]["train_size"] + rows[0]["test_size"] if rows else 0
    modes = sorted({r["mode"] for r in rows})
    by_key: dict[tuple[str, int], list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["mode"], r["train_size_requested"]), []).append(r)

    lines: list[str] = []
    lines.append("# Split sweep — train_size sweep × 3 repeats × mode\n")
    lines.append(f"Usable issues (with valid A–F category): **{n_total}**\n")

    # ------------------------------------------------------------------
    # Strategy descriptions
    # ------------------------------------------------------------------
    lines.append("## Strategies\n")
    lines.append(
        "### Strategy A — `default` (bounded per-repo cap)\n"
        "1. Compute per-category seed quotas via **largest-remainder "
        "rounding** (snake / serpentine recall-merge), one issue per "
        "quota slot.\n"
        "2. For each category, prefer an issue from a repo we have not "
        "yet claimed; fall back to an already-claimed repo only if the "
        "unclaimed pool is exhausted.\n"
        "3. After the seed phase, for every claimed repo R, pull in "
        "additional issues up to a per-repo cap "
        "`m_R = round(train_size / |claimed_repos|)` (largest-remainder "
        "rounding so the total stays near `train_size`).\n"
        "\n"
        "**Goal**: train size ≈ requested, broad repo coverage, "
        "low-but-not-zero leakage. On this 200-issue / 11-repo dataset "
        "leakage is essentially 100% because the cap is a few issues "
        "per repo, not the whole repo.\n"
    )
    lines.append(
        "### Strategy B — `repo_disjoint` (strict, whole-repo isolation)\n"
        "1. Decide how many repos `N` to claim: choose the smallest "
        "`N` such that `Σ issue_counts[claimed_repos] ≥ train_size`.\n"
        "2. Move **every** issue from each of those `N` repos to "
        "train; everything else goes to test.\n"
        "3. By construction, `test_repo_leakage_pct == 0`.\n"
        "\n"
        "**Goal**: zero contamination between train and test. Trade-off: "
        "actual train size is coarse (whole repos), so it jumps in steps "
        "and is rarely equal to the requested size.\n"
    )

    # ------------------------------------------------------------------
    # Per-strategy section
    # ------------------------------------------------------------------
    lines.append(
        "### Strategy C — `greedy_issue` (issue-level greedy)\n"
        "1. Snake through the **6 categories × 11 repos** cross-tab; "
        "at each step pick an issue from the next (repo, category) "
        "cell.\n"
        "2. If we still need more issues to hit `train_size`, top up "
        "from the smallest-claimed-repo pool.\n"
        "\n"
        "**Goal**: hit `train_size` exactly, maximise coverage of "
        "both repos and categories. Trade-off: once we exhaust the "
        "fresh-repo pool we must reuse claimed repos, so leakage is "
        "no longer guaranteed to be 0.\n"
    )
    for mode in modes:
        lines.append(f"## Strategy `{mode}` — full table (per repeat)\n")
        lines.append("| req | rep | train | test | train % | "
                     "unique repos | leakage % | cats covered |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|---|")
        for r in rows:
            if r["mode"] != mode:
                continue
            cats = r["train_category_counts"]
            covered = sum(1 for c in "ABCDEF" if c in cats)
            cats_str = f"{covered}/6"
            train_pct = round(100.0 * r["train_size"] / n_total, 1)
            lines.append(
                f"| {r['train_size_requested']} | {r['repeat']} | "
                f"{r['train_size']} | {r['test_size']} | "
                f"{train_pct} | {r['train_unique_repos']} | "
                f"{r['test_repo_leakage_pct']} | {cats_str} |"
            )
        lines.append("")
        lines.append(f"### Strategy `{mode}` — averages over 3 repeats\n")
        lines.append("| req | train (mean) | test (mean) | "
                     "leakage % (mean) | repos (mean) | cats covered |")
        lines.append("|---:|---:|---:|---:|---:|---|")
        for ts in sorted({k[1] for k in by_key if k[0] == mode}):
            rep_rows = by_key[(mode, ts)]
            n = len(rep_rows)
            avg_train = sum(x["train_size"] for x in rep_rows) / n
            avg_test = sum(x["test_size"] for x in rep_rows) / n
            avg_leak = sum(x["test_repo_leakage_pct"] for x in rep_rows) / n
            avg_repos = sum(x["train_unique_repos"] for x in rep_rows) / n
            covered = sum(
                1 for c in "ABCDEF"
                if all(c in x["train_category_counts"] for x in rep_rows)
            )
            lines.append(
                f"| {ts} | {avg_train:.1f} | {avg_test:.1f} | "
                f"{avg_leak:.1f} | {avg_repos:.1f} | {covered}/6 |"
            )
        lines.append("")

    # ------------------------------------------------------------------
    # Side-by-side averages
    # ------------------------------------------------------------------
    lines.append("## Side-by-side comparison — averages over 3 repeats\n")
    lines.append("| req | A train | A leakage | A cats | "
                 "B train | B leakage | B cats | "
                 "C train | C leakage | C cats |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    ts_set = sorted({r["train_size_requested"] for r in rows})
    for ts in ts_set:
        a = by_key.get(("default", ts), [])
        b = by_key.get(("repo_disjoint", ts), [])
        c = by_key.get(("greedy_issue", ts), [])
        if not a or not b or not c:
            continue
        a_train = sum(x["train_size"] for x in a) / len(a)
        a_leak = sum(x["test_repo_leakage_pct"] for x in a) / len(a)
        a_cats = sum(
            1 for c2 in "ABCDEF"
            if all(c2 in x["train_category_counts"] for x in a)
        )
        b_train = sum(x["train_size"] for x in b) / len(b)
        b_leak = sum(x["test_repo_leakage_pct"] for x in b) / len(b)
        b_cats = sum(
            1 for c2 in "ABCDEF"
            if all(c2 in x["train_category_counts"] for x in b)
        )
        c_train = sum(x["train_size"] for x in c) / len(c)
        c_leak = sum(x["test_repo_leakage_pct"] for x in c) / len(c)
        c_cats = sum(
            1 for c2 in "ABCDEF"
            if all(c2 in x["train_category_counts"] for x in c)
        )
        lines.append(
            f"| {ts} | {a_train:.1f} | {a_leak:.1f} | {a_cats}/6 | "
            f"{b_train:.1f} | {b_leak:.1f} | {b_cats}/6 | "
            f"{c_train:.1f} | {c_leak:.1f} | {c_cats}/6 |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, default=Path("data/index.jsonl"))
    p.add_argument("--train-sizes", type=int, nargs="+",
                   default=[20, 40, 60, 80, 100, 120, 140, 160, 180])
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--out", type=Path, default=Path("results"),
                   help="Directory for sweep.jsonl and sweep.md")
    args = p.parse_args()

    rows = [json.loads(l) for l in args.index.read_text().splitlines() if l.strip()]
    print(f"Loaded {len(rows)} index rows from {args.index}")

    results = run_sweep(rows, args.train_sizes, args.repeats)
    write_jsonl(args.out / "sweep.jsonl", results)
    write_markdown(args.out / "sweep.md", results)
    print(f"Wrote {args.out / 'sweep.jsonl'} and {args.out / 'sweep.md'}")


if __name__ == "__main__":
    main()
