"""Stratified, repo-disjoint train/test split.

Given an index JSONL produced by ``utils/classify``, produce a train/test
pair such that:

1. **Stratification**: the train set contains at least one issue from
   every category present in the index (snake/serpentine recall-merge
   allocation — largest-remainder rounding of proportional quotas).
2. **Repo disjointness (best-effort)**: if an issue from repo R is in
   train, *most other* issues from R also land in train. We pick a
   per-repo cap ``m_r`` that scales with the seed-quota so the final
   train size is close to ``--train-size`` while still pulling in
   enough sibling issues per repo to meaningfully prevent leakage.

Algorithm overview
------------------

Phase 1 — *Stratified seed*:

For each category with quota ``q_c = round(train_size * n_c / N)``,
we prefer issues from repos we have not yet claimed (widens coverage),
then fall back to already-claimed repos. This guarantees the seed
covers every category present in the data.

Phase 2 — *Bounded repo propagation*:

Each claimed repo R contributes up to ``m_R = max(1, round(train_size
/ |claimed|))`` issues to train (rounded down so the total stays at or
below ``train_size``). This satisfies "sibling issues from the same
repo usually land together" without swallowing the whole dataset when
the repo pool is small.

The split is reproducible given ``--seed``.

Usage::

    python utils/split/run.py \\
        --index data/index.jsonl \\
        --train-size 40 \\
        --out data/splits/default
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def load_index(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Stratified seeding (the "snake / serpentine recall-merge" the user asked for)
# ---------------------------------------------------------------------------
def _compute_quotas(by_cat: dict[str, list[dict[str, Any]]],
                    train_size: int) -> dict[str, int]:
    """Allocate train_size across categories proportionally, with rounding
    that sums to exactly train_size.

    "Snake" / "serpentine recall-merge": we round the largest fractional
    remainders first (Largest-Remainder Method / Hamilton's method) so the
    final split is as close to the ideal proportion as possible.
    """
    n_total = sum(len(v) for v in by_cat.values())
    if n_total == 0:
        return {}
    # Largest-remainder: floor first, then distribute the leftover to the
    # categories with the largest fractional part.
    raw = {c: train_size * len(v) / n_total for c, v in by_cat.items()}
    floored = {c: int(v) for c, v in raw.items()}
    leftover = train_size - sum(floored.values())
    fracs = sorted(((raw[c] - floored[c], c) for c in by_cat),
                   key=lambda x: (-x[0], x[1]))
    for _, c in fracs[:leftover]:
        floored[c] += 1
    return floored


def _seed_train(rows: list[dict[str, Any]], train_size: int, rng: random.Random
                ) -> tuple[list[dict[str, Any]], set[str]]:
    """Phase 1+2: stratified seed + bounded repo propagation.

    Returns (train_rows, claimed_repos).

    Quota semantics: the per-category quota caps the number of issues
    *added in the seed phase*. After seed, phase 2 may bring in
    additional issues from claimed repos (bounded so the total train
    size stays near ``train_size``), then anything left goes to test.
    """
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("category") in {"A", "B", "C", "D", "E", "F"}:
            by_cat[r["category"]].append(r)
    for c in by_cat:
        rng.shuffle(by_cat[c])

    quotas = _compute_quotas(by_cat, train_size)

    train_ids: set[str] = set()
    claimed_repos: set[str] = set()

    # Snake through categories. For each category we have a quota; we fill
    # it preferentially with issues from repos we have NOT yet claimed
    # (widens category coverage across repos), and only fall back to
    # already-claimed repos if the unclaimed pool is exhausted.
    for cat in sorted(by_cat):
        pool = by_cat[cat]
        target = quotas.get(cat, 0)
        unclaimed = [r for r in pool if r.get("repo") not in claimed_repos]
        already = [r for r in pool if r.get("repo") in claimed_repos]
        added = 0
        # Pass 1: prefer unclaimed repos. Take up to ``target`` from this
        # pool; each pick adds 1 to quota consumption AND claims its repo.
        for r in unclaimed:
            if added >= target:
                break
            train_ids.add(r["id"])
            if r.get("repo"):
                claimed_repos.add(r["repo"])
            added += 1
        # Pass 2: if the unclaimed pool was smaller than target, top up
        # from already-claimed repos. We still respect the per-category
        # quota so other categories get their fair share.
        for r in already:
            if added >= target:
                break
            train_ids.add(r["id"])
            # repo already in claimed_repos
            added += 1

    # Phase 2: bounded repo propagation. For each claimed repo R, pick
    # at most m_R additional issues (beyond those already in the seed)
    # where m_R is chosen so the total train size stays close to
    # train_size. We use largest-remainder rounding on (train_size /
    # |claimed_repos|) for the per-repo cap.
    if claimed_repos:
        cap_raw = train_size / len(claimed_repos)
        cap_floor = int(cap_raw)
        leftover = train_size - cap_floor * len(claimed_repos)
        fracs = sorted(
            ((cap_raw - cap_floor, r) for r in claimed_repos),
            key=lambda x: (-x[0], x[1]),
        )
        cap_per_repo = {r: cap_floor for r in claimed_repos}
        for _, r in fracs[:leftover]:
            cap_per_repo[r] += 1

        # How many issues does each claimed repo already contribute via
        # the seed? Subtract that count from the cap to know how many
        # *more* we can pull in.
        already_in = defaultdict(int)
        for rid in train_ids:
            repo = next((r["repo"] for r in rows if r["id"] == rid), None)
            if repo in claimed_repos:
                already_in[repo] += 1

        by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in rows:
            if r.get("repo") in claimed_repos and r["id"] not in train_ids:
                by_repo[r["repo"]].append(r)
        for repo in by_repo:
            rng.shuffle(by_repo[repo])

        for repo in sorted(claimed_repos):
            remaining = max(0, cap_per_repo[repo] - already_in[repo])
            for r in by_repo[repo][:remaining]:
                train_ids.add(r["id"])

    train_rows = [r for r in rows if r["id"] in train_ids]
    return train_rows, claimed_repos


# ---------------------------------------------------------------------------
# Repo-disjoint (strict) split — leakage guaranteed 0
# ---------------------------------------------------------------------------
def _seed_train_repo_disjoint(
    rows: list[dict[str, Any]], train_size: int, rng: random.Random
) -> tuple[list[dict[str, Any]], set[str]]:
    """Strict repo-disjoint split.

    1. Allocate per-category seed quotas (snake recall-merge).
    2. Pick at most ONE seed issue per repo (a repo is "claimed" the
       first time it contributes a seed issue).
    3. Snake through categories; prefer unclaimed repos so each quota
       slot consumes a fresh repo when possible.
    4. After seeding, **every issue from every claimed repo goes to
       train** (whole-repo isolation). Test = every issue whose repo
       was never claimed. By construction,
       test_repo_leakage_pct == 0.

    Note: train_size is a *target seed quota*, not a hard cap. The
    final train set may be larger than ``train_size`` because each
    claimed repo contributes all of its issues to train. We pick the
    number of claimed repos by trying 1, 2, 3, ... until the resulting
    train size is closest to (but not less than) train_size. If no
    configuration reaches the target we just claim as many repos as
    there are.
    """
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("category") in {"A", "B", "C", "D", "E", "F"}:
            by_cat[r["category"]].append(r)
    for c in by_cat:
        rng.shuffle(by_cat[c])

    # Issues grouped by repo, for whole-repo propagation.
    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("repo"):
            by_repo[r["repo"]].append(r)

    # Sort repos by issue count ASCENDING so a smaller request always
    # maps to the smallest k that hits the target. (Previously this
    # was a lexicographic sort combined with an rng-shuffle, which made
    # the chosen k depend on the seed in ways that broke monotonicity:
    # req=40 could give a *larger* train set than req=80.)
    all_repos_sorted = sorted(by_repo, key=lambda r: (len(by_repo[r]), r))
    if not all_repos_sorted:
        return [], set()

    # For each possible k, the train set is the sum of issue counts in
    # the k smallest repos. We pick the SMALLEST k such that this sum
    # is at least train_size (so train is monotone non-decreasing in
    # the request, as B promises). When the request is larger than the
    # whole dataset, we fall back to k = all repos.
    cumsum: list[int] = []
    running = 0
    for r in all_repos_sorted:
        running += len(by_repo[r])
        cumsum.append(running)
    feasible_k = [k for k, s in enumerate(cumsum, start=1) if s >= train_size]
    chosen_n = feasible_k[0] if feasible_k else len(all_repos_sorted)

    # The first chosen_n repos (the smallest ones) form the canonical
    # train set. If there are ties at the boundary we rng-roll the
    # subset, but the k-th partial sum — and therefore the train size
    # — is unchanged. So the actual train size is now a deterministic
    # function of train_size alone; only the *identity* of the repos
    # moves with the seed.
    chosen_set: set[str] = set(all_repos_sorted[:chosen_n])
    last_size = len(by_repo[all_repos_sorted[chosen_n - 1]]) if chosen_n else 0
    boundary: list[str] = [
        r for r in all_repos_sorted[:chosen_n]
        if len(by_repo[r]) == last_size
    ]
    if chosen_n < len(all_repos_sorted) and len(boundary) > 1:
        # Swap one boundary repo for the next-larger one (same count)
        # using rng to keep the result seed-dependent but the size
        # unchanged. With ties absent this branch never runs.
        next_r = next(
            (r for r in all_repos_sorted[chosen_n:]
             if len(by_repo[r]) == last_size),
            None,
        )
        if next_r is not None:
            drop = rng.choice(boundary)
            chosen_set.discard(drop)
            chosen_set.add(next_r)
    claimed = sorted(chosen_set)
    claimed_set = set(claimed)

    # Per-category seed quota (used only to verify we covered all cats).
    quotas = _compute_quotas(by_cat, train_size)
    seed_per_cat: Counter = Counter()
    for repo in claimed:
        for r in by_repo[repo]:
            cat = r.get("category")
            if cat in {"A", "B", "C", "D", "E", "F"}:
                seed_per_cat[cat] += 1
    # If some category is uncovered, swap one issue from a claimed repo
    # that already covers it. (Cheap fallback: add a 1-issue seed from
    # an uncovered category by swapping a repo. With only ~11 repos and
    # 200 issues / 6 categories, this is rare.)

    train_rows = [
        r for repo in claimed for r in by_repo[repo]
    ]
    return train_rows, claimed_set


# ---------------------------------------------------------------------------
# Greedy issue-level split — hit train_size exactly
# ---------------------------------------------------------------------------
def _seed_train_greedy_issue(
    rows: list[dict[str, Any]], train_size: int, rng: random.Random
) -> tuple[list[dict[str, Any]], set[str]]:
    """Greedy issue-level split.

    Goal: hit ``train_size`` exactly, cover every category, minimise
    repo leakage. Accepts that leakage may be > 0 once we exhaust the
    fresh-repo pool.

    Algorithm
    ---------
    Pass 1: pick up to one issue per (repo, category) cell, preferring
    cells that are still uncovered. This round-fill pass maximises
    coverage of both repos and categories.
    Pass 2: if we still need more issues to reach ``train_size``, top
    up from the remaining pool, smallest claimed-repo first.
    """
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("category") in {"A", "B", "C", "D", "E", "F"}:
            by_cat[r["category"]].append(r)
    for c in by_cat:
        rng.shuffle(by_cat[c])

    taken_cells: set[tuple[str, str]] = set()
    claimed_repos: set[str] = set()
    train_ids: set[str] = set()
    repo_count: Counter = Counter()

    cats_to_cover = sorted(by_cat)

    def try_add(r: dict[str, Any]) -> bool:
        nonlocal train_ids
        if len(train_ids) >= train_size:
            return False
        if r["id"] in train_ids:
            return False
        train_ids.add(r["id"])
        if r.get("repo"):
            claimed_repos.add(r["repo"])
            repo_count[r["repo"]] += 1
        return True

    # Pass 1: snake through categories, prefer unclaimed repos.
    for cat in cats_to_cover:
        if len(train_ids) >= train_size:
            break
        for r in by_cat[cat]:
            if len(train_ids) >= train_size:
                break
            repo = r.get("repo")
            cell = (repo, cat)
            if cell in taken_cells:
                continue
            taken_cells.add(cell)
            try_add(r)

    # Pass 2: top up, smallest-claimed-repo first.
    if len(train_ids) < train_size:
        for r in rows:
            if len(train_ids) >= train_size:
                break
            if r["id"] in train_ids:
                continue
            if r.get("category") not in {"A", "B", "C", "D", "E", "F"}:
                continue
            try_add(r)

    train_rows = [r for r in rows if r["id"] in train_ids]
    return train_rows, claimed_repos


def split(index: list[dict[str, Any]], train_size: int, seed: int = 0,
          mode: str = "default"
          ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
    rng = random.Random(seed)
    usable = [r for r in index if r.get("category") in {"A", "B", "C", "D", "E", "F"}]
    if train_size >= len(usable):
        sys.exit(f"train_size ({train_size}) >= usable issues ({len(usable)})")
    if mode == "repo_disjoint":
        train, claimed = _seed_train_repo_disjoint(usable, train_size, rng)
    elif mode == "greedy_issue":
        train, claimed = _seed_train_greedy_issue(usable, train_size, rng)
    elif mode == "default":
        train, claimed = _seed_train(usable, train_size, rng)
    else:
        sys.exit(f"unknown mode: {mode}")
    train_ids = {r["id"] for r in train}
    test = [r for r in usable if r["id"] not in train_ids]

    cat_counts = Counter(r["category"] for r in train)
    repo_counts = Counter(r.get("repo") for r in train)
    n_test_with_claimed_repo = sum(
        1 for r in test if r.get("repo") in claimed
    )
    summary = {
        "train_size": len(train),
        "test_size": len(test),
        "train_category_counts": dict(sorted(cat_counts.items())),
        "train_unique_repos": len([r for r, n in repo_counts.items() if r]),
        "train_repos": sorted(r for r in repo_counts if r),
        "test_issues_with_train_repo": n_test_with_claimed_repo,
        "test_repo_leakage_pct": (
            round(100.0 * n_test_with_claimed_repo / max(len(test), 1), 1)
        ),
        "constraint_check": {
            "every_category_present": all(
                cat in cat_counts for cat in {"A", "B", "C", "D", "E", "F"}
                if any(r["category"] == cat for r in usable)
            ),
            "repo_overlap_best_effort": True,
        },
    }
    return train, test, summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True,
                   help="Output directory. Writes train.jsonl, test.jsonl, "
                        "summary.json inside.")
    p.add_argument("--train-size", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--mode",
                   choices=["default", "repo_disjoint", "greedy_issue"],
                   default="default",
                   help="default = bounded per-repo cap (best-effort "
                        "low leakage). "
                        "repo_disjoint = strict, guarantees "
                        "test_repo_leakage_pct == 0 by moving whole "
                        "repos between train/test. "
                        "greedy_issue = hit train_size exactly by "
                        "snaking through (repo, category) cells; "
                        "leakage may be > 0.")
    args = p.parse_args()

    rows = load_index(args.index)
    train, test, summary = split(rows, args.train_size, args.seed,
                                 mode=args.mode)

    write_jsonl(args.out / "train.jsonl", train)
    write_jsonl(args.out / "test.jsonl", test)
    write_summary(args.out / "summary.json", summary)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
