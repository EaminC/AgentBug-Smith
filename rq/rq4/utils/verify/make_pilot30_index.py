"""make_pilot30_index.py — regenerate the pilot-30 issue indexes.

Background
----------
Pilot-30 is a 5-issue × 6-combo × 2-skill = 60-rollout design. The
5 issues were picked once (seed=20260909) from the test split of
``issue_index_mini-swe-agent_40.jsonl`` and then matched by id across
the other 5 combos' test splits.

This script regenerates all 12 pilot-30 index files (6 combos ×
{with,without}-issue-1351 variants) from the 6 full combo indexes
that ``utils/verify/build_verify.py`` writes. After this, any machine
that has the full indexes can reproduce the pilot-30 selection
deterministically — no manual curation required.

Inputs (must already exist, written by ``build_verify.py``):
    data/verify/issue_index_<agent>_<train_size>.jsonl   (6 files)

Outputs (overwritten if present):
    data/verify/issue_index_pilot30_<agent>_<train_size>.jsonl
    data/verify/issue_index_pilot30_<agent>_<train_size>_no1351.jsonl

Usage
-----
    python utils/verify/make_pilot30_index.py                # write all 12
    python utils/verify/make_pilot30_index.py --dry-run     # print what would be written

Selection rule (matches docs/progress.md §9):
    seed = 20260909
    candidates = rows in issue_index_mini-swe-agent_40.jsonl with split == 1
    picked_5 = random.sample(candidates, 5)
    For each combo C, the pilot30 index for C is the subset of
    issue_index_<C>.jsonl whose id ∈ picked_5 (preserving the file
    order of the full index).
    The ``_no1351`` variant drops issue-1351 (pre-existing build
    error in agentscope that the pool didn't catch).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_ROOT = REPO_ROOT / "data" / "verify"

# Anchor combo: the 5 issues are picked from this combo's test split.
# Picking from the smallest train size (40) maximises the test pool.
ANCHOR_COMBO = "mini-swe-agent_40"

# The 6 combos × 2 skill modes the pilot covers.
ALL_COMBOS = [
    "mini-swe-agent_40", "mini-swe-agent_60", "mini-swe-agent_80",
    "openhands_40", "openhands_60", "openhands_80",
]

# Reproducible selection seed (matches docs/progress.md §9).
PILOT_SEED = 20260909

# Build-broken issue that the _no1351 variants exclude.
SKIP_ISSUE_ID = "issue-1351"


def _load_index(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_index(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _pick_5(anchor_rows: list[dict]) -> list[str]:
    """Return 5 issue ids deterministically sampled from the test split
    of the anchor combo's index. Order matches ``random.sample``."""
    test_pool = [r for r in anchor_rows if r.get("split") == 1]
    if len(test_pool) < 5:
        sys.exit(
            f"anchor index {VERIFY_ROOT / f'issue_index_{ANCHOR_COMBO}.jsonl'} "
            f"has only {len(test_pool)} split=1 rows; cannot pick 5."
        )
    rng = random.Random(PILOT_SEED)
    picked = rng.sample(test_pool, 5)
    return [r["id"] for r in picked]


def _subset_by_ids(full_rows: list[dict], ids: set[str]) -> list[dict]:
    """Filter ``full_rows`` to those whose id is in ``ids``, preserving
    the order of ``full_rows`` (which is deterministic across runs)."""
    return [r for r in full_rows if r["id"] in ids]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would be written, do not write.")
    args = ap.parse_args()

    anchor_path = VERIFY_ROOT / f"issue_index_{ANCHOR_COMBO}.jsonl"
    if not anchor_path.exists():
        sys.exit(
            f"missing anchor index: {anchor_path}\n"
            f"Run `python utils/verify/build_verify.py` first."
        )

    anchor_rows = _load_index(anchor_path)
    picked_ids = _pick_5(anchor_rows)
    picked_set = set(picked_ids)
    print(f"anchor: {anchor_path.name}  (split=1 pool={sum(1 for r in anchor_rows if r['split']==1)})")
    print(f"picked (seed={PILOT_SEED}): {sorted(picked_ids)}")
    print()

    if SKIP_ISSUE_ID in picked_set:
        no1351_ids = picked_set - {SKIP_ISSUE_ID}
    else:
        no1351_ids = picked_set
        print(f"note: anchor did not contain {SKIP_ISSUE_ID}; "
              f"_no1351 variants will be identical to the full variants.")

    total_written = 0
    for combo in ALL_COMBOS:
        full_path = VERIFY_ROOT / f"issue_index_{combo}.jsonl"
        if not full_path.exists():
            print(f"  ! {full_path.name} missing; skipping combo {combo!r}",
                  file=sys.stderr)
            continue
        full_rows = _load_index(full_path)
        full_subset = _subset_by_ids(full_rows, picked_set)
        no1351_subset = _subset_by_ids(full_rows, no1351_ids)

        full_out = VERIFY_ROOT / f"issue_index_pilot30_{combo}.jsonl"
        no1351_out = VERIFY_ROOT / f"issue_index_pilot30_{combo}_no1351.jsonl"

        print(f"{combo}:")
        print(f"  {full_out.relative_to(REPO_ROOT)}  "
              f"({len(full_subset)} rows: {sorted(r['id'] for r in full_subset)})")
        print(f"  {no1351_out.relative_to(REPO_ROOT)}  "
              f"({len(no1351_subset)} rows: {sorted(r['id'] for r in no1351_subset)})")

        if not args.dry_run:
            _write_index(full_out, full_subset)
            _write_index(no1351_out, no1351_subset)
            total_written += 2

    if args.dry_run:
        print(f"\n(dry-run) no files written.")
    else:
        print(f"\nwrote {total_written} pilot-30 index files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
