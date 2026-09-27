# utils — dataset acquisition, preparation, skill training, evaluation

Five sub-components, run in order:

1. `download/` — pull `EaminC/AgentBug-Smith` `all_combined_f2p` dataset
   to `data/raw/`. Uses `git sparse-checkout` (no auth needed) — only
   the target subdirectory is fetched, not the whole repo.
2. `classify/` — for each downloaded issue, ask the LLM (default
   `openai/gpt-4o-mini` via `https://api.tu-zi.com`) for a primary
   category from `docs/taxonomy.md` and write a flat index at
   `data/index.jsonl`.
3. `split/` — read `data/index.jsonl` and carve out a stratified,
   repo-disjoint train/test split. Default outputs at
   `data/splits/<split-name>/{train,test}.jsonl`.
4. `train/` — for each `(agent, train_size)` pair we want to evaluate,
   train a per-repo **skill** (`agent/skills/<agent>/<train_size>/...`)
   by letting the agent summarise each train repo's patterns. Skills
   are the *intervention* — they get injected into the agent at solve
   time to test whether per-repo guidance improves solve rate.
5. `verify/` — build the **evaluation (verify) pool** and per-skill
   **index files**. The pool is a *patch-stripped* copy of every
   `data/raw` issue (so the agent can't cheat by reading the gold
   diff). Each of the 6 skills we trained gets its own index that
   assigns every issue to `split=0` (train, excluded) or `split=1`
   (test, used by the solver). Solver script `solve.py` (next) drives
   the agent on each test issue and records pass/fail.

No agent harness in `download/classify/split/verify/` — just scripts.
Only `train/` invokes the agent (and only once per (repo, skill),
the work that runs an LLM to summarise the repo).

## Why not an agent?

The user explicitly asked for this. The classification, split, and
verify-pool-build steps are mechanical (one LLM call per issue for
classification; pure algorithms for split and verify pool). Using
an agent here would add tool-call noise, nondeterminism, and cost.
The classification LLM call itself goes straight through the
OpenAI SDK against the tu-zi gateway.

The **train** step *does* use an agent — there each repo is too
complex for a deterministic script, and the per-repo summary is the
whole point of the experiment.

## Files

- `download/run.py`     — sparse-checkout the dataset
- `classify/run.py`     — batch LLM classification → index.jsonl
- `split/run.py`        — stratified, repo-disjoint train/test split
- `train/train_skill.py` — per-repo skill writer (LLM)
- `train/run_all.sh`    — train all 6 skills end-to-end
- `verify/build_verify.py` — build patch-stripped pool + 6 per-skill indices
- `pipeline.py`         — runs download → classify → split end-to-end
- `config.json`         — shared tunables (LLM endpoint, paths, defaults)
- `README.md`           — this file

## Pipeline

```bash
source agent/.venv/bin/activate
source utils/.env

# Steps 1–3: dataset prep (no agent)
python utils/pipeline.py                       # full dataset
python utils/pipeline.py --limit 20            # 20-issue dry run

# Step 4: train 6 skills (one LLM call per repo per skill)
bash utils/train/run_all.sh                    # 2 agents × 3 sizes
FORCE=1 bash utils/train/run_all.sh            # rebuild all skills

# Step 5: build verify pool + 6 indices
python utils/verify/build_verify.py            # idempotent
python utils/verify/build_verify.py --audit    # leak-vector scan
```

Each step can also be run individually:

```bash
python utils/download/run.py --out data/raw
python utils/classify/run.py \
    --in data/raw/results/all_combined_f2p \
    --out data/index.jsonl
python utils/split/run.py \
    --index data/index.jsonl \
    --train-size 40 \
    --out data/splits/default
python utils/train/train_skill.py \
    --agent openhands --train-size 60 \
    --mode repo_disjoint --seed 42
python utils/verify/build_verify.py
```

## Verify pool design

The pool (`data/verify/_pool/<owner>__<name>__<issue-id>/`) is a
one-shot, *patch-stripped* copy of every raw issue directory. The
repo-prefixed dir naming is deliberate: GitHub issue numbers are
repo-scoped, and the same number in two different repos refers to
two different bugs. The earlier id-only scheme
(`_pool/<issue-id>/`) silently overwrote content for the 8
colliding ids, so 16 index rows pointed at the wrong pool content.
The repo prefix and a global `pool_dir_uniqueness` audit check
make any regression loud.

To prevent the agent from cheating by reading the gold solution:

- `issue_<NNN>.json` → metadata only. The keys `linked_prs[].patch`,
  `linked_prs[].base_sha`, and `linked_prs[].head_sha` are removed.
  Public PR metadata (number, state, title, url, merged, base_branch)
  is preserved. `repo` and `id` are re-stamped so each dir is
  self-describing.
- `generated_patch.diff` → never copied.
- `run.log` (the agent's stdout, contains the agent's attempted
  patch diffs) → copied only if it has no `diff --git` header;
  otherwise dropped. Empirically 185/200 run.logs are dropped.
- `f2p.txt` / `dockerbuild.txt` → copied only if diff-free.
- Everything else (`env.dockerfile`, `agentsmith_fail2pass_*.py`,
  `summary.json`, `agentsmith_stat.json`) is copied verbatim.

Per-skill index files (`data/verify/issue_index_<agent>_<train_size>.jsonl`)
have one row per issue with:

```json
{
  "split": 1,                              // 0=train(excluded), 1=test(solve)
  "id": "issue-1077",
  "repo": "strands-agents/harness-sdk",
  "category": "B",
  "verify_dir": "data/verify/_pool/strands-agents__harness-sdk__issue-1077",
  "test_relpath": "tests/agentsmith_fail2pass_1077.py",
  "f2p_status": true,
  "source_split": {"agent": "openhands", "train_size_requested": 40,
                   "mode": "repo_disjoint", "seed": 42}
}
```

The split assignment is `(repo, id)` composite-keyed to avoid a
latent dedup bug in `utils/split/run.py` where 8 ids that collide
across repos (`issue-563`, `issue-974`, …) used to silently vanish
from the test set.

## Split algorithm notes

The split has two objectives that can pull in opposite directions on
small datasets:

1. **Stratified coverage**: train must contain every category present
   in the index. Quotas per category are computed by *largest-remainder
   rounding* on the proportional share `train_size * n_c / N` (Hamilton's
   method). This is the "snake / serpentine recall-merge" — the
   rounding leftover is allocated to the categories with the largest
   fractional parts so the total exactly hits `train_size`.
2. **Repo leakage reduction**: once a repo lands in the seed, sibling
   issues from the same repo are preferred for train over test, *up to
   a per-repo cap* `m_r ≈ train_size / |claimed_repos|`. This is the
   "smart" part: with `n=11` repos in the dataset, the cap is
   `40 / 11 ≈ 4` issues per repo, which means most issues from any
   claimed repo still go to test. That's the unavoidable trade-off when
   the dataset is small relative to `train_size`; the summary reports
   `test_repo_leakage_pct` so you can see how much overlap remains.

The split is deterministic given `--seed`.

## `utils/verify/solve.py` — solver

Drives the agent over every `split=1` row of an index file, with
or without the matching `SKILL.md` injected into the prompt.

```bash
# Sanity-check the prompt assembly + verify-dir resolution for one
# issue, no LLM cost, no docker.
python utils/verify/solve.py dry-run \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1077 \
    --skill-mode all

# Real evaluation (requires upstream repo clones under $AGENTSMITH_ROOT):
python utils/verify/solve.py run \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1077 \
    --skill-mode all

# After runs land, score them (apply patch → test → pass/fail):
python utils/verify/solve.py score \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1077
```

The pilot prints a one-screen summary per `(row, skill_mode)` pair
with prompt size, pool files, base SHA, and the resolved SKILL.md.
The full design (modes, output layout, blocker list) is in
`docs/handoff.md` §4.1.

