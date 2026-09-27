# Progress Report — RQ4 (Migration, 2026-09-11)

*For advisor review. Migration-focused snapshot for the week of
2026-09-07 → 2026-09-11.*

The full project status lives in `docs/progress.md`. This file is a
short, week-scoped delta: **what was finished this week, why the repo
was packaged for migration, and how to bring the new server back to a
runnable state in one command.**

---

## 1. What was finished this week

### 1.1 Pilot-20 (6-combo × 80-rollout batch)
* Recorded in commit `2e15e1f` ("docs(rq4): record 6-combo × 80-rollout
  pilot-20 final results").
* 80 rollouts across 4 cells (mini-swe-agent / openhands × with-skill /
  without-skill, train_size=40). All 12 cells of the broader design —
  including sizes 60 and 80 — were *attempted* but produced zero
  non-empty patches because of two infrastructure bugs (see 1.3).
* 13/80 docker images built successfully, but **pass@1 = 0%** in every
  cell. The pilot was sufficient to rule out a strong skill-transfer
  effect on this task set at train_size=40, but not to measure a small
  effect.

### 1.2 Pilot-30 (5-issue × 6-combo design)
* 5 issues × 6 combos × 2 skill modes = **60 rollouts**, excluding
  issue-1351 in 4 of 6 combos because of an unrelated agentscope
  docker-build failure.
* Patches extracted for **47/60 rollouts** after the fixes in 1.3.
* Eval stage hit a Docker engine I/O error (`write
  …/io.containerd.metadata.v1.bolt/meta.db: input/output error`)
  on the local Mac. Cleared by `rm -rf
  ~/Library/Containers/com.docker.docker/Data/*` (after
  `osascript -e 'quit app "Docker Desktop"'`). All rollouts need to
  be re-evaluated on the new server.
* Headline: this pilot rules out *patch production* as the blocker
  (47/60 produced parseable diffs) and isolates *semantic correctness*
  as the open question.

### 1.3 Two infrastructure bugs fixed (the real reason pilot-20 was 0/12)

Both bugs are documented in commit history but summarised here for
context:

1. **`OPENAI_API_BASE` not reaching the LLM call.** `solve.py` built
   the docker `env` dict from `os.environ`, but `OPENAI_API_BASE` only
   lived in `agent/config/.env` and was never sourced. The container
   saw `OPENAI_API_KEY` but no base URL, so LiteLLM fell through to
   `api.openai.com` and got `401 Invalid API key`. Both agents
   silently produced empty patches.

2. **Scratch files included in `git diff`.** Both agents created
   scratch files (`repro.py`, `patch_openai_model.py`, `result.log`)
   while debugging, and the captured diff captured all of them. Patches
   either failed `git apply` (file exists in workspace) or applied
   with broken scaffolding.

Both fixes live on `main`; nothing extra needs to happen on the new
server beyond `git pull`.

---

## 2. Why we're migrating

The Mac's local Docker Desktop accumulated **~466 GB of overlay /
containerd data** over the pilot-20 and pilot-30 runs, twice filling
the system partition mid-experiment and stopping the orchestrator
with `OSError: [Errno 28] No space left on device`. The new server
will have a clean disk and a fresh Docker install; this file is the
guide for getting back to a runnable state.

---

## 3. One-shot setup on the new server

```bash
git clone https://github.com/1123qqa/ICLR2027.git
cd RQ4
bash scripts/setup-all.sh
```

`scripts/setup-all.sh` (new this week) chains the three component
setup scripts and adds the host-level preflight that the old workflow
required the user to remember:

* checks `git`, `python3 ≥ 3.10`, `uv`, `curl`, `docker`, optional
  `pandoc`;
* confirms the Docker daemon is reachable (not just `docker` on PATH)
  and that the repo volume has ≥30 GB free;
* runs `scripts/setup.sh` (mini-swe-agent venv + clone + env),
  `scripts/setup-openhands.sh` (OpenHands CLI + env), and
  `scripts/setup-utils.sh` (utils venv + .env + sparse-checkout smoke);
* prints the four commands you typically run next.

Override knobs (all optional):

```bash
TUZI_API_KEY=sk-...          bash scripts/setup-all.sh
SKIP_OPENHANDS=1             bash scripts/setup-all.sh   # CI w/o UI
SKIP_PANDOC=1                bash scripts/setup-all.sh   # no PDF build
```

---

## 4. TODO after migration (priority-ordered)

| # | Task | Effort | Owner |
|---|---|---|---|
| 1 | `bash scripts/setup-all.sh` on new server, confirm smoke tests pass. | 30 min | me |
| 2 | Re-derive the verify pool: `python utils/verify/build_verify.py --audit`. Recovers `data/verify/_pool/` + `issue_index_*.jsonl` on the new host. | 2 h | me |
| 3 | Re-train the 6 skills (or reuse committed `agent/skills/` if the trainer is deterministic). `bash utils/train/run_all.sh`. | 4 h | me |
| 4 | Re-run pilot-30 **eval only** (patches already extracted, ~50 MB on disk) using `utils/verify/standalone_batch_f2p.py` to get a clean pass@1 table. | 1 h | me |
| 5 | Re-run pilot-30 for openhands_40/60/80 — those three cells were killed by the disk-full incident before producing any data. | 6 h | me |
| 6 | Decide whether to expand to pilot-50 / pilot-100 once the eval pipeline is stable. | 1 day | me + advisor |
| 7 | Re-render `docs/progress.pdf` once section 9 of `progress.md` is finalised (`cd docs && make pdf`). | 5 min | me |
| 8 | Add the new server's hostname / IP to `agent/config/.env.example` (or a new `docs/hosts.md`) so future migrations don't lose context. | 5 min | me |

---

## 5. Risks / open questions for the new server

* **Docker storage driver.** The Mac used `overlay2` via Docker Desktop's
  virtual disk. Linux server with `btrfs` / `xfs` should be fine, but
  if the host is on ZFS, increase the dataset reservation; the
  pilot-20 batch held ~50 GB of intermediate layers.
* **OpenHands CLI install path.** The script installs to
  `~/.local/bin/openhands`. On a headless server this is fine — the
  CLI is the only thing we use; the Web UI is not started.
* **API key.** `TUZI_API_KEY` is committed in clear text in the three
  setup scripts (long-standing). Rotate before exposing the new
  server to anyone outside the lab.
* **Pilot-30 sample size.** 5 issues is too small to disentangle
  "agent is wrong" from "issue is too hard". The open question for the
  advisor is whether to expand to pilot-50/100 first, or first fix the
  underlying semantic-correctness problem on a few hand-checked issues.

---

## 6. File diff this week

```
A  scripts/setup-all.sh          — one-shot bootstrap (new)
M  README.md                     — points new readers at setup-all.sh
M  docs/progress.md              — extends §9 with pilot-30 patch-extraction fixes
A  scripts/run_pilot30.sh        — full 6-combo batch
A  scripts/run_pilot30_no1351.sh — drops issue-1351 (build-broken)
A  utils/verify/_openhands_sdk_driver.py
A  utils/verify/batch_f2p_eval.py
A  utils/verify/f2p_eval.py
A  utils/verify/plot_pilot30.py
A  utils/verify/reextract_patches.py
A  utils/verify/smoke_test.py
A  utils/verify/standalone_batch_f2p.py
M  utils/verify/solve.py         — sources agent/config/.env; widens scratch-file exclude list
A  results/rq4/pilot30_scores.csv
A  results/rq4/figures/pilot30_cumulative_pass1.png
```

(Local-only, not tracked: `agent/openhands-sdk/`, `logs/`.)
