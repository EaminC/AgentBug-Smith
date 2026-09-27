"""Distribution stats over the 200-issue index.

Writes ``results/split/distribution.md`` and ``results/split/distribution.json``
with three views:

1. Overall counts (total, by category, by repo)
2. Per-repo breakdown: how many issues each repo contributes, and the
   category histogram inside each repo
3. Category × repo cross-tab: which categories appear in which repos

Run::

    python utils/split/dist_stats.py --index data/index.jsonl --out results/split
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def load_index(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=Path("data/index.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("results/split"))
    args = ap.parse_args()
    rows = load_index(args.index)
    args.out.mkdir(parents=True, exist_ok=True)

    n = len(rows)
    cat_counter = Counter(r.get("category") for r in rows)
    repo_counter = Counter(r.get("repo") for r in rows)
    # Per-repo category histogram.
    repo_cats: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        repo_cats[r.get("repo")][r.get("category")] += 1
    # Category × repo cross-tab.
    cross: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        cross[r.get("category")][r.get("repo")] += 1

    # ----- Markdown -----
    md: list[str] = []
    md.append("# Distribution of the 200-issue index\n")
    md.append(f"Total issues: **{n}**\n")
    md.append(f"Distinct repos: **{len(repo_counter)}**\n")
    md.append(f"Distinct categories: **{len(cat_counter)}** "
              f"({', '.join(sorted(cat_counter))})\n")

    md.append("## Per-category counts\n")
    md.append("| category | count | share % |")
    md.append("|---|---:|---:|")
    for cat in sorted(cat_counter):
        md.append(f"| {cat} | {cat_counter[cat]} | "
                  f"{100.0 * cat_counter[cat] / n:.1f} |")

    md.append("")
    md.append("## Per-repo counts (descending)\n")
    md.append("| repo | issues | share % | categories present |")
    md.append("|---|---:|---:|---|")
    for repo, cnt in repo_counter.most_common():
        cats_present = ", ".join(
            f"{c}({repo_cats[repo][c]})"
            for c in sorted(repo_cats[repo])
        )
        md.append(f"| {repo} | {cnt} | {100.0 * cnt / n:.1f} | "
                  f"{cats_present} |")

    md.append("")
    md.append("## Category × repo cross-tab\n")
    repos_sorted = [r for r, _ in repo_counter.most_common()]
    cats_sorted = sorted(cat_counter)
    header = "| category | " + " | ".join(repos_sorted) + " | total |"
    sep = "|---|" + "|".join(["---:"] * (len(repos_sorted) + 1)) + "|"
    md.append(header)
    md.append(sep)
    for cat in cats_sorted:
        cells = [str(cross[cat].get(repo, 0)) for repo in repos_sorted]
        total = sum(int(c) for c in cells)
        md.append(f"| {cat} | " + " | ".join(cells) + f" | **{total}** |")
    # Repo total row.
    totals = [str(repo_counter[repo]) for repo in repos_sorted]
    grand = sum(int(t) for t in totals)
    md.append("| **total** | " + " | ".join(f"**{t}**" for t in totals) +
              f" | **{grand}** |")

    md.append("")
    md.append("## Repo size statistics\n")
    sizes = sorted(repo_counter.values())
    md.append(f"- min = {sizes[0]}, max = {sizes[-1]}, "
              f"mean = {sum(sizes) / len(sizes):.1f}, "
              f"median = {sizes[len(sizes) // 2]}")
    md.append(f"- size distribution: "
              + ", ".join(f"{s}:{sizes.count(s)}" for s in sorted(set(sizes))))
    md.append("")
    md.append("## Category entropy per repo\n")
    md.append("| repo | issues | # categories | entropy (nats) |")
    md.append("|---|---:|---:|---:|")
    import math
    for repo, cnt in repo_counter.most_common():
        ncat = len(repo_cats[repo])
        h = -sum((c / cnt) * math.log(c / cnt)
                 for c in repo_cats[repo].values())
        md.append(f"| {repo} | {cnt} | {ncat} | {h:.2f} |")

    md_path = args.out / "distribution.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    # ----- JSON -----
    json_payload = {
        "total_issues": n,
        "distinct_repos": len(repo_counter),
        "distinct_categories": sorted(cat_counter),
        "category_counts": dict(sorted(cat_counter.items())),
        "repo_counts": dict(sorted(repo_counter.items(),
                                   key=lambda x: -x[1])),
        "repo_category_breakdown": {
            r: dict(sorted(c.items())) for r, c in repo_cats.items()
        },
        "category_x_repo": {
            c: dict(sorted(cross[c].items(),
                           key=lambda x: -x[1]))
            for c in sorted(cross)
        },
    }
    (args.out / "distribution.json").write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote {md_path}")
    print(f"Wrote {args.out / 'distribution.json'}")


if __name__ == "__main__":
    main()
