# Split sweep — train_size sweep × 3 repeats × mode

Usable issues (with valid A–F category): **200**

## Strategies

### Strategy A — `default` (bounded per-repo cap)
1. Compute per-category seed quotas via **largest-remainder rounding** (snake / serpentine recall-merge), one issue per quota slot.
2. For each category, prefer an issue from a repo we have not yet claimed; fall back to an already-claimed repo only if the unclaimed pool is exhausted.
3. After the seed phase, for every claimed repo R, pull in additional issues up to a per-repo cap `m_R = round(train_size / |claimed_repos|)` (largest-remainder rounding so the total stays near `train_size`).

**Goal**: train size ≈ requested, broad repo coverage, low-but-not-zero leakage. On this 200-issue / 11-repo dataset leakage is essentially 100% because the cap is a few issues per repo, not the whole repo.

### Strategy B — `repo_disjoint` (strict, whole-repo isolation)
1. Decide how many repos `N` to claim: choose the smallest `N` such that `Σ issue_counts[claimed_repos] ≥ train_size`.
2. Move **every** issue from each of those `N` repos to train; everything else goes to test.
3. By construction, `test_repo_leakage_pct == 0`.

**Goal**: zero contamination between train and test. Trade-off: actual train size is coarse (whole repos), so it jumps in steps and is rarely equal to the requested size.

### Strategy C — `greedy_issue` (issue-level greedy)
1. Snake through the **6 categories × 11 repos** cross-tab; at each step pick an issue from the next (repo, category) cell.
2. If we still need more issues to hit `train_size`, top up from the smallest-claimed-repo pool.

**Goal**: hit `train_size` exactly, maximise coverage of both repos and categories. Trade-off: once we exhaust the fresh-repo pool we must reuse claimed repos, so leakage is no longer guaranteed to be 0.

## Strategy `default` — full table (per repeat)

| req | rep | train | test | train % | unique repos | leakage % | cats covered |
|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 0 | 28 | 172 | 14.0 | 11 | 100.0 | 6/6 |
| 20 | 1 | 29 | 171 | 14.5 | 10 | 98.8 | 6/6 |
| 20 | 2 | 29 | 171 | 14.5 | 10 | 98.8 | 6/6 |
| 40 | 0 | 54 | 146 | 27.0 | 11 | 100.0 | 6/6 |
| 40 | 1 | 53 | 147 | 26.5 | 11 | 100.0 | 6/6 |
| 40 | 2 | 53 | 147 | 26.5 | 11 | 100.0 | 6/6 |
| 60 | 0 | 76 | 124 | 38.0 | 11 | 100.0 | 6/6 |
| 60 | 1 | 78 | 122 | 39.0 | 11 | 100.0 | 6/6 |
| 60 | 2 | 76 | 124 | 38.0 | 11 | 100.0 | 6/6 |
| 80 | 0 | 96 | 104 | 48.0 | 11 | 100.0 | 6/6 |
| 80 | 1 | 101 | 99 | 50.5 | 11 | 100.0 | 6/6 |
| 80 | 2 | 96 | 104 | 48.0 | 11 | 100.0 | 6/6 |
| 100 | 0 | 124 | 76 | 62.0 | 11 | 100.0 | 6/6 |
| 100 | 1 | 118 | 82 | 59.0 | 11 | 100.0 | 6/6 |
| 100 | 2 | 119 | 81 | 59.5 | 11 | 100.0 | 6/6 |
| 120 | 0 | 139 | 61 | 69.5 | 11 | 100.0 | 6/6 |
| 120 | 1 | 139 | 61 | 69.5 | 11 | 100.0 | 6/6 |
| 120 | 2 | 137 | 63 | 68.5 | 11 | 100.0 | 6/6 |
| 140 | 0 | 154 | 46 | 77.0 | 11 | 100.0 | 6/6 |
| 140 | 1 | 157 | 43 | 78.5 | 11 | 100.0 | 6/6 |
| 140 | 2 | 148 | 52 | 74.0 | 11 | 100.0 | 6/6 |
| 160 | 0 | 167 | 33 | 83.5 | 11 | 100.0 | 6/6 |
| 160 | 1 | 168 | 32 | 84.0 | 11 | 100.0 | 6/6 |
| 160 | 2 | 168 | 32 | 84.0 | 11 | 100.0 | 6/6 |
| 180 | 0 | 185 | 15 | 92.5 | 11 | 100.0 | 6/6 |
| 180 | 1 | 183 | 17 | 91.5 | 11 | 100.0 | 6/6 |
| 180 | 2 | 185 | 15 | 92.5 | 11 | 100.0 | 6/6 |

### Strategy `default` — averages over 3 repeats

| req | train (mean) | test (mean) | leakage % (mean) | repos (mean) | cats covered |
|---:|---:|---:|---:|---:|---|
| 20 | 28.7 | 171.3 | 99.2 | 10.3 | 6/6 |
| 40 | 53.3 | 146.7 | 100.0 | 11.0 | 6/6 |
| 60 | 76.7 | 123.3 | 100.0 | 11.0 | 6/6 |
| 80 | 97.7 | 102.3 | 100.0 | 11.0 | 6/6 |
| 100 | 120.3 | 79.7 | 100.0 | 11.0 | 6/6 |
| 120 | 138.3 | 61.7 | 100.0 | 11.0 | 6/6 |
| 140 | 153.0 | 47.0 | 100.0 | 11.0 | 6/6 |
| 160 | 167.7 | 32.3 | 100.0 | 11.0 | 6/6 |
| 180 | 184.3 | 15.7 | 100.0 | 11.0 | 6/6 |

## Strategy `greedy_issue` — full table (per repeat)

| req | rep | train | test | train % | unique repos | leakage % | cats covered |
|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 0 | 21 | 179 | 10.5 | 9 | 98.3 | 4/6 |
| 20 | 1 | 20 | 180 | 10.0 | 9 | 98.3 | 3/6 |
| 20 | 2 | 20 | 180 | 10.0 | 10 | 99.4 | 3/6 |
| 40 | 0 | 43 | 157 | 21.5 | 11 | 100.0 | 6/6 |
| 40 | 1 | 43 | 157 | 21.5 | 11 | 100.0 | 6/6 |
| 40 | 2 | 43 | 157 | 21.5 | 11 | 100.0 | 6/6 |
| 60 | 0 | 63 | 137 | 31.5 | 11 | 100.0 | 6/6 |
| 60 | 1 | 63 | 137 | 31.5 | 11 | 100.0 | 6/6 |
| 60 | 2 | 62 | 138 | 31.0 | 11 | 100.0 | 6/6 |
| 80 | 0 | 83 | 117 | 41.5 | 11 | 100.0 | 6/6 |
| 80 | 1 | 84 | 116 | 42.0 | 11 | 100.0 | 6/6 |
| 80 | 2 | 84 | 116 | 42.0 | 11 | 100.0 | 6/6 |
| 100 | 0 | 106 | 94 | 53.0 | 11 | 100.0 | 6/6 |
| 100 | 1 | 106 | 94 | 53.0 | 11 | 100.0 | 6/6 |
| 100 | 2 | 106 | 94 | 53.0 | 11 | 100.0 | 6/6 |
| 120 | 0 | 128 | 72 | 64.0 | 11 | 100.0 | 6/6 |
| 120 | 1 | 128 | 72 | 64.0 | 11 | 100.0 | 6/6 |
| 120 | 2 | 128 | 72 | 64.0 | 11 | 100.0 | 6/6 |
| 140 | 0 | 148 | 52 | 74.0 | 11 | 100.0 | 6/6 |
| 140 | 1 | 148 | 52 | 74.0 | 11 | 100.0 | 6/6 |
| 140 | 2 | 147 | 53 | 73.5 | 11 | 100.0 | 6/6 |
| 160 | 0 | 168 | 32 | 84.0 | 11 | 100.0 | 6/6 |
| 160 | 1 | 168 | 32 | 84.0 | 11 | 100.0 | 6/6 |
| 160 | 2 | 168 | 32 | 84.0 | 11 | 100.0 | 6/6 |
| 180 | 0 | 188 | 12 | 94.0 | 11 | 100.0 | 6/6 |
| 180 | 1 | 188 | 12 | 94.0 | 11 | 100.0 | 6/6 |
| 180 | 2 | 188 | 12 | 94.0 | 11 | 100.0 | 6/6 |

### Strategy `greedy_issue` — averages over 3 repeats

| req | train (mean) | test (mean) | leakage % (mean) | repos (mean) | cats covered |
|---:|---:|---:|---:|---:|---|
| 20 | 20.3 | 179.7 | 98.7 | 9.3 | 3/6 |
| 40 | 43.0 | 157.0 | 100.0 | 11.0 | 6/6 |
| 60 | 62.7 | 137.3 | 100.0 | 11.0 | 6/6 |
| 80 | 83.7 | 116.3 | 100.0 | 11.0 | 6/6 |
| 100 | 106.0 | 94.0 | 100.0 | 11.0 | 6/6 |
| 120 | 128.0 | 72.0 | 100.0 | 11.0 | 6/6 |
| 140 | 147.7 | 52.3 | 100.0 | 11.0 | 6/6 |
| 160 | 168.0 | 32.0 | 100.0 | 11.0 | 6/6 |
| 180 | 188.0 | 12.0 | 100.0 | 11.0 | 6/6 |

## Strategy `repo_disjoint` — full table (per repeat)

| req | rep | train | test | train % | unique repos | leakage % | cats covered |
|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 0 | 21 | 177 | 10.5 | 6 | 0.0 | 6/6 |
| 20 | 1 | 21 | 177 | 10.5 | 6 | 0.0 | 6/6 |
| 20 | 2 | 21 | 177 | 10.5 | 6 | 0.0 | 6/6 |
| 40 | 0 | 47 | 151 | 23.5 | 8 | 0.0 | 6/6 |
| 40 | 1 | 47 | 151 | 23.5 | 8 | 0.0 | 6/6 |
| 40 | 2 | 47 | 151 | 23.5 | 8 | 0.0 | 6/6 |
| 60 | 0 | 71 | 126 | 35.5 | 9 | 0.0 | 6/6 |
| 60 | 1 | 71 | 126 | 35.5 | 9 | 0.0 | 6/6 |
| 60 | 2 | 71 | 126 | 35.5 | 9 | 0.0 | 6/6 |
| 80 | 0 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 80 | 1 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 80 | 2 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 100 | 0 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 100 | 1 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 100 | 2 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 120 | 0 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 120 | 1 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 120 | 2 | 121 | 74 | 60.5 | 10 | 0.0 | 6/6 |
| 140 | 0 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 140 | 1 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 140 | 2 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 160 | 0 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 160 | 1 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 160 | 2 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 180 | 0 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 180 | 1 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |
| 180 | 2 | 200 | 0 | 100.0 | 11 | 0.0 | 6/6 |

### Strategy `repo_disjoint` — averages over 3 repeats

| req | train (mean) | test (mean) | leakage % (mean) | repos (mean) | cats covered |
|---:|---:|---:|---:|---:|---|
| 20 | 21.0 | 177.0 | 0.0 | 6.0 | 6/6 |
| 40 | 47.0 | 151.0 | 0.0 | 8.0 | 6/6 |
| 60 | 71.0 | 126.0 | 0.0 | 9.0 | 6/6 |
| 80 | 121.0 | 74.0 | 0.0 | 10.0 | 6/6 |
| 100 | 121.0 | 74.0 | 0.0 | 10.0 | 6/6 |
| 120 | 121.0 | 74.0 | 0.0 | 10.0 | 6/6 |
| 140 | 200.0 | 0.0 | 0.0 | 11.0 | 6/6 |
| 160 | 200.0 | 0.0 | 0.0 | 11.0 | 6/6 |
| 180 | 200.0 | 0.0 | 0.0 | 11.0 | 6/6 |

## Side-by-side comparison — averages over 3 repeats

| req | A train | A leakage | A cats | B train | B leakage | B cats | C train | C leakage | C cats |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 20 | 28.7 | 99.2 | 6/6 | 21.0 | 0.0 | 6/6 | 20.3 | 98.7 | 3/6 |
| 40 | 53.3 | 100.0 | 6/6 | 47.0 | 0.0 | 6/6 | 43.0 | 100.0 | 6/6 |
| 60 | 76.7 | 100.0 | 6/6 | 71.0 | 0.0 | 6/6 | 62.7 | 100.0 | 6/6 |
| 80 | 97.7 | 100.0 | 6/6 | 121.0 | 0.0 | 6/6 | 83.7 | 100.0 | 6/6 |
| 100 | 120.3 | 100.0 | 6/6 | 121.0 | 0.0 | 6/6 | 106.0 | 100.0 | 6/6 |
| 120 | 138.3 | 100.0 | 6/6 | 121.0 | 0.0 | 6/6 | 128.0 | 100.0 | 6/6 |
| 140 | 153.0 | 100.0 | 6/6 | 200.0 | 0.0 | 6/6 | 147.7 | 100.0 | 6/6 |
| 160 | 167.7 | 100.0 | 6/6 | 200.0 | 0.0 | 6/6 | 168.0 | 100.0 | 6/6 |
| 180 | 184.3 | 100.0 | 6/6 | 200.0 | 0.0 | 6/6 | 188.0 | 100.0 | 6/6 |
