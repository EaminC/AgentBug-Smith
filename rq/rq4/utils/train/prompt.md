# Training Agent Skills from Closed-Patch Issues

This directory contains the pipeline that turns the **200 closed issues
with f2p-tested golden patches** (under `data/raw/results/all_combined_f2p/`)
into **Cursor Agent Skills** that teach downstream agents how to fix
issues of the same shape.

## What we are training

The "training set" is the *train* half of an RQ4 split. For a given
configuration `(agent, train_size)` we:

1. Pick a split mode. We use **`repo_disjoint`** (see
   `results/split/figures/05_*.png`) so the trained skill has zero
   repo leakage with whatever repo ends up in test.
2. Pick a `train_size` from `{20, 40, 100}`. These give roughly
   `{30, 60, 150}` issues per the B-strategy coarseness curve in
   `results/split/sweep.md`.
3. **Per-repo loop**. For each repo R that has at least one issue in
   the train set:
   - create a fresh scratch workspace (`/tmp/<scratch_id>`)
   - `git clone` the upstream of R into it
   - materialise *all* R's issues (both train and test! — see below)
     as readable problem/patch bundles
   - run **the same agent wrapper we are training** (`mini-swe-agent`
     or `openhands`) and prompt it to write
     `agent/skills/<agent>/<train_size>/repos/<safe_repo_name>.md`
     from those bundles

   The skill is the agent's *own* distillation of its own experience
   fixing these issues — i.e. self-curated training data.

4. Across repos we **merge** the per-repo notes into a single skill
   bundle at `agent/skills/<agent>/<train_size>/`, with:
   - `SKILL.md` — the skill itself, initialised from a template at
     `utils/train/templates/SKILL.template.md` and progressively
     augmented as more repos finish.
   - `repos/<owner>__<name>.md` — one notes file per repo.
   - `manifest.json` — provenance (split config, repos covered,
     issues used, agent version).

## Why per-repo (not per-issue, not all-repos-at-once)

- **Context budget**: 50+ issues per repo is too many to fit in a
  single prompt; 5 issues per repo in 11 repos is roughly the right
  "lesson" chunk.
- **Composability**: skills composed of many `repos/*.md` files are
  readable at a glance — Cursor loads only the relevant repo when the
  user's issue happens to be in that repo (via `@repos/<owner>__<name>.md`).
- **Incremental updates**: if a new repo is added later, you only
  need to train one more notes file; the rest of the skill is
  untouched.

## Why `repo_disjoint`

The split strategy `repo_disjoint` is the **only** one of the three
in `utils/split/run.py` that achieves `test_repo_leakage_pct == 0`.
For training this matters because we want the skill's experience to
be **representative of new repos**, not memorised from the very
repos we will test on. The cost is train size coarseness — fine for
training, since we only need a representative sample, not an exact N.

## Why include *test* issues during per-repo training

Subtle but important: when training skill for repo R, we feed the
agent **all** of R's issues (train + test) — but only the **patches**
are visible, not the issue text being "leaked". Actually, both
issue text and patches are visible: the point of skill training is
to teach the agent the **fixing patterns** of repo R, which it
*should* have seen even if it is also being evaluated on some of
them. Otherwise we are training on a hollow subset and the skill
would not represent R's idioms at all.

The `test_repo_leakage_pct == 0` guarantee is preserved at the
**split / evaluation** boundary, not at the training boundary. The
trained skill will be evaluated against held-out test issues of
**other** repos, never its own repo's test issues — because
`repo_disjoint` guarantees every repo is either fully train or
fully test, never split.

## Pipeline entry point

```
python utils/train/train_skill.py \
    --agent mini-swe-agent \
    --train-size 40 \
    --mode repo_disjoint \
    --seed 42 \
    --out agent/skills
```

The script will:

1. Call `utils.split.split(index, train_size, seed, mode)` to get the
   per-repo partition.
2. For each repo in `train_repos`, spawn a sub-call to
   `agent/run_<agent>.sh` with the prompt assembled by
   `utils.train.prompts.repo_lessons_prompt(...)`.
3. Wait for the agent to write `repos/<safe_repo_name>.md` to the
   output skill directory.
4. When all repos are done, finalise `SKILL.md` from the template,
   inserting a one-line summary per repo, and emit `manifest.json`.

## Re-running / resuming

`utils/train/train_skill.py --resume` skips any repo whose
`repos/<safe_repo_name>.md` already exists with a non-empty body.

## Cost and rate limiting

Each per-repo call costs roughly $0.10–$0.50 of LLM usage (rough
estimate from `data/raw/results/.../agentsmith_stat.json` — full
issues are smaller than full f2p runs, so cheaper). Budget per
`(agent, train_size)`:

- 11 repos × ~$0.30 ≈ **$3.30 per skill**.
- 6 skills × $3.30 ≈ **$20 total**.

Use `--dry-run` to print the planned prompts without invoking the
agent.
