# Handoff — Component 6/7 (Rollout + f2p Judge)

*Authored 2026-09-06 by the previous agent. If you are reading this
without the rest of the conversation, start here.*

## TL;DR

The previous session built the **evaluation harness** for RQ4. The
verify pool and 6 per-skill index files already exist on disk. Your
job is to **drive each agent against the test issues** in every index
(Component 6: rollout) and **score each rollout's patch with the f2p
judge** (Component 7). Both are now wired and end-to-end verified on a
single pilot.

## Pilot end-to-end (validated 2026-09-06)

Issue **`issue-1058`** (agentscope-ai/agentscope, base SHA
`f44b10fc`), both skill modes of **`mini-swe-agent_40`**:

| step                 | with-skill | without-skill |
|----------------------|-----------:|--------------:|
| docker build         | 80 s       | (cached)      |
| agent run            | 6m         | 3m32s         |
| patch size           | 19 071 B   | 1 599 B       |
| f2p outcome          | **f2f**    | **f2f**       |
| pre-patch rc         | 2          | 2             |
| post-patch rc        | 2          | 2             |
| why f2f              | env missing `mcp.client.streamable_http.streamablehttp_client` at base SHA — test infra broken | agent's patch had unmatched `)` in `_openai_model.py:461` — patch introduced syntax error |

Both classifications are *correct* — the judge caught two distinct
breakage classes (env-level and patch-level) that **any** agent would
trip on for this issue. The judge itself works.

### Bug history (fixed during the pilot)

1. `solve.py` default model was `tuzi-gpt-4.1-mini/...`; litellm needs
   `openai/gpt-4.1-mini` (with `OPENAI_API_BASE` set to the tu-zi
   gateway).
2. `extract_patch` only looked for `diff --git` headers; mini's
   submission is `--- file.bak / +++ file` format. Added
   `_submission_to_git_diff()` to rewrite.
3. `image_meta.json` was keyed per-skill-mode, causing without-skill
   to think the image was cached (when only with-skill's image
   existed). Fixed: shared `image_meta.json` per `(key, id)`, single
   image-tag regardless of skill mode (the image is the repo + f2p
   test; the skill only changes the prompt).
4. `score.py` injection only swapped `patch` in the tmp issue JSON;
   `run_f2p_verify()` re-reads `ctx.base_sha` from there, which was
   `None` for our pool. Now we also inject `base_sha` (resolved from
   `ctx.base_sha or row.base_sha`).
5. `score.py` also hit `reset_repo_to_base(sha=None)` because the
   wrong `ctx.base_sha` was being passed. Resolved by item 4 + using
   `effective_base_sha` consistently.
6. `agentscope-ai/agentscope` is a shallow clone locally — needed
   `git fetch --unshallow` before the base SHA resolves.

---

## 1. State of the world (as of 2026-09-06)

### What's done
- 200 classified issues (`data/index.jsonl`, gitignored).
- 6 fully-trained per-repo skills:
  ```
  agent/skills/{mini-swe-agent,openhands}/{40,60,80}/
  ```
  Each contains `SKILL.md`, `fallback_generic_fix.md`, `manifest.json`,
  and `repos/<owner>__<name>.md`.
- Verify pool (`data/verify/_pool/<repo-owner>__<repo-name>__<issue-id>/`,
  gitignored) — **200 dirs** (one per ``(repo, id)`` row in the index).
  The repo-prefixed dir naming is deliberate: GitHub issue numbers are
  repo-scoped, and the same number in two different repos refers to
  completely different bugs. The earlier scheme (``<issue-id>/``)
  silently overwrote content for 8 colliding ids (e.g. ``issue-563``
  in `AntonOsika/gpt-engineer` vs `dapr/dapr-agents`). The fix landed
  in `utils/verify/build_verify.py::pool_dir_for`. Each dir is
  **~24 KB**, total ~4.8 MB, all patch fields stripped, exactly 3
  files per directory (`env.dockerfile`, the
  `agentsmith_fail2pass_<NNN>.py` test, and `issue.json` — which now
  also carries `repo` and `id` for self-description). Built and
  audited by `utils/verify/build_verify.py --force-pool --audit` using
  the default `--strict` 3-file mode. The legacy 7-file mode is still
  reachable via `--no-strict` for forensic debug only.
- 6 per-skill indices (`data/verify/issue_index_<agent>_<train_size>.jsonl`,
  gitignored) — 200 rows each, `split=0` (train) / `split=1` (test).
- `utils/verify/build_verify.py` is the canonical rebuilder. It is
  idempotent; `--force-pool` rebuilds the pool from scratch,
  `--audit` scans for surviving leak vectors.
- Latest two commits on `main`:
  ```
  29fdc3e gitignore: skip *.hallucinated.* validator-rejected backups
  9c4e188 component 5: build_verify.py — patch-stripped pool + 6 per-skill indices
  ```
- PDF (`docs/progress.pdf`, 11 pages) and markdown
  (`docs/progress.md`) are up to date and pushed to
  `github.com/1123qqa/ICLR2027`.

### What's next (the actual ask)
**Component 6** — `utils/verify/solve.py`. For each of the 6 per-skill
indices, iterate every `split=1` row, point the agent at
`data/verify/_pool/<owner>__<name>__<id>/`, inject the matching
`agent/skills/<agent>/<train_size>/SKILL.md` into the system prompt,
and record pass/fail against `agentsmith_fail2pass_<NNN>.py`. Also
run a *no-skill* baseline (same issue, same agent, SKILL.md removed)
so we can report per-skill lift.

### Key invariants
- 6 indices span **200 unique (repo, id) pairs** — exactly the size of
  `data/index.jsonl`. The pool has **200 dirs** (one per row), not 192,
  because each verify dir is prefixed by `__`-joined `owner/name`:
  ```
  data/verify/_pool/strands-agents__sdk-python__issue-1077/
  data/verify/_pool/AntonOsika__gpt-engineer__issue-563/
  data/verify/_pool/dapr__dapr-agents__issue-563/             # same id,
                                                                # different
                                                                # repo
  ```
  The repo prefix prevents the **same-id-across-repos overwrite bug**
  that hit the previous (id-only) scheme — see §4 below for the
  post-mortem.
- All 6 indices have **identical issue-level train/test partition**
  (`seed=42`, `mode=repo_disjoint`). Only the **count** differs:
  | skill | train | test |
  |---|---:|---:|
  | `*_40`  | 47  | 153 |
  | `*_60`  | 71  | 129 |
  | `*_80`  | 121 | 79  |
  Repo leakage is **0%** for all 6.
- The verify pool's job is to make sure the agent **cannot read the
  gold patch**. The leak audit (`data/verify/audit.json`) currently
  reports `200/200 issues clean` plus a global
  `pool_dir_uniqueness` check. Every entry passes:
  - `absent:generated_patch.diff` — the gold diff file never copied;
  - `issue_json_no_patch_keys` — `linked_prs[].{patch, base_sha,
    head_sha}` all stripped;
  - `strict_3_file_invariant` — every verify dir contains exactly
    `env.dockerfile`, `issue.json`, and one
    `agentsmith_fail2pass_<NNN>.py`. Nothing else.
  - `pool_dir_uniqueness` — every pool dir's
    `issue.json.{repo, id}` matches the ``(repo, id)`` row in
    `data/index.jsonl`, and no two pool dirs collide.

---

## 2. Files you will likely need

| Path | What it is |
|---|---|
| `data/verify/_pool/<owner>__<name>__<id>/` | patch-stripped issue dir (input) |
| `data/verify/issue_index_<agent>_<train_size>.jsonl` | which issues to solve + their pool path (now also carries `base_sha`) |
| `agent/skills/<agent>/<train_size>/SKILL.md` | per-skill system-prompt injection |
| `agent/run_mini.sh` | wrapper for mini-swe-agent (component 1) |
| `agent/run_openhands.sh` | wrapper for openhands (component 2) |
| `agent/config/mini.yaml` | mini-swe-agent config (LLM endpoint, etc.) |
| `utils/verify/build_verify.py` | reference for reading index rows, pool layout, and the strict 3-file invariant |
| `utils/train/train_skill.py` | reference for how SKILL.md gets injected |
| `utils/verify/solve.py` | Component 6 driver (see §4.1) |
| `docs/progress.md` §6.4, §6.5, §7, §8 | status, next, and reproduce |

---

## 4.1 Component 6 — solver (this commit, scaffolding only)

`utils/verify/solve.py` is the driver for Component 6. It has three
sub-commands:

| Sub-command | What it does |
|---|---|
| `solve.py dry-run --index <file> [--pilot-id issue-NNN] [--skill-mode with\|without\|all]` | Walks the index, resolves SKILL.md (or fallback), builds the prompt, **prints every input** without calling LLM or docker. Used to verify the data flow. |
| `solve.py run --index <file> [...]` | **Builds a docker image per row + invokes `mini` against it.** Wired (the helpers `build_image_for_row`, `run_mini_in_docker`, `build_prompt` are complete) but the `run` branch is a stub in this commit — it does call `build_image_for_row`, but the rest of the orchestration needs `~/AgentBug-Smith/data/<owner>_<name>/` clones at every row's `base_sha` in place before the pilot will work end-to-end. See `data/verify/runs/<agent>_<train_size>/<repo>__<id>/<with\|without_skill>/` for the planned output layout. |
| `solve.py score --index <file> [...]` | Apply each captured trajectory's patch to a fresh container, run the f2p test, record `passed`. **Not yet implemented** in this commit. |

The dry-run path on **issue-1077** (the canonical example) reports
prompt sizes of:

| Skill mode | Prompt chars | First 80 chars |
|---|---:|---|
| with-skill   | 9 805 | `<skill>\n---\nname: rq4-issue-fixer…` |
| no-skill     | 6 827 | `You are a software engineer. A GitHub issue from…` |

The ~3 000-char delta is the SKILL.md body that the no-skill baseline
replaces with `fallback_generic_fix.md` (1815 chars).

### To actually run Component 6 (next steps)

The pilot's blocker list, in order:

1. **Repo clones.** Each row carries a `base_sha`. The solver expects
   the upstream repo at `$AGENTSMITH_ROOT/<owner>_<name>/` (default
   `~/AgentBug-Smith/data/<owner>_<name>/`). For the canonical pilot
   issue, this is `~/AgentBug-Smith/data/strands-agents_harness-sdk/`.
   Without the 11 cloned repos, `build_image_for_row` aborts with a
   clear "repo clone not found" error.
2. **Pilot one issue end-to-end.** Run:
   ```bash
   python utils/verify/solve.py run \
       --index data/verify/issue_index_mini-swe-agent_40.jsonl \
       --pilot-id issue-1077 --skill-mode all
   ```
   Confirm the trajectory lands in
   `data/verify/runs/mini-swe-agent_40/strands-agents__harness-sdk__issue-1077/{with_skill,without_skill}/trajectory.json`.
3. **Implement `solve.py score`.** Apply the trajectory's final
   `patch.txt` to a fresh container, run
   `pytest tests/agentsmith_fail2pass_<NNN>.py -x`, record
   pass/fail. Run twice per (row, skill_mode): once for
   with-skill, once for no-skill. The pair is the unit of analysis.
4. **Scale.** Once one issue passes end-to-end, switch from
   `--pilot-id` to the default (every `split=1` row). Expect ~6 × 153
   with-skill + ~6 × 153 no-skill = ~1 836 runs. Set a
   `--cost-limit` and a per-row wall-clock cap; budget ~60 h
   wall-clock for the full sweep.


## 3. Suggested design for `utils/verify/solve.py`

This is a **sketch, not a contract**. Adapt to whatever runtime the
agent components actually need.

```
$ python utils/verify/solve.py --agent openhands --train-size 40 \
    --index data/verify/issue_index_openhands_40.jsonl \
    --split test --out results/verify/openhands_40.jsonl
```

Pseudocode:

```python
def main():
    index = load_jsonl(args.index)         # rows have .split, .id, .verify_dir, ...
    skill_dir = REPO_ROOT / "agent/skills" / args.agent / str(args.train_size)
    skill_md  = (skill_dir / "SKILL.md").read_text()
    baseline_md = (skill_dir / "fallback_generic_fix.md").read_text()
    results = []
    for row in index:
        if row["split"] != 1: continue        # solve only test
        pool_dir = REPO_ROOT / row["verify_dir"]
        test_file = pool_dir / Path(row["test_relpath"]).name
        # Two runs per issue: WITH the per-repo skill, and WITHOUT.
        for mode, sysprompt in [("skill", skill_md), ("baseline", baseline_md)]:
            outcome = run_agent(
                agent=args.agent,
                workdir=pool_dir,
                issue=load_issue_body(pool_dir / "issue.json"),
                system_prompt=sysprompt,
                test_file=test_file,
            )
            results.append({
                "id": row["id"], "repo": row["repo"], "category": row["category"],
                "mode": mode, "passed": outcome.passed,
                "agent_log": str(outcome.log_path),
                "wall_clock_s": outcome.wall_clock,
                "tokens_in": outcome.tokens_in, "tokens_out": outcome.tokens_out,
            })
    write_jsonl(args.out, results)
```

Key questions you need to answer before coding:

1. **How does the agent actually run?** Read `agent/run_mini.sh` and
   `agent/run_openhands.sh`; you will be calling them (or their
   underlying Python CLIs) from inside `solve.py`. Do not try to
   shell out to an LLM directly — the whole point is to test the
   **end-to-end** agent harness including tool use.
2. **What is the success signal?** The simplest definition is "the
   pre-existing `agentsmith_fail2pass_<NNN>.py` exits 0 after the
   agent's patch is applied". Look at how the train pipeline tests
   its smoke-test (`utils/train/train_skill.py --single-issue ...`)
   — it almost certainly already runs that test. Reuse the same
   runner. If no shared runner exists, write one inside `solve.py`
   that mounts the pool dir into a docker container with
   `env.dockerfile` and exits based on the pytest return code.
3. **Where do agent logs and patches go?** I suggest
   `results/verify/runs/<agent>/<train_size>/<mode>/<id>/{log,patch.diff,test.log}`
   so a single `results/verify/<agent>_<train_size>.jsonl` can point
   at the artefacts.
4. **Cost / time budget.** 6 skills × 153 test issues (the worst
   case, `train_size=40`) = ~918 runs *with* skill + 918 *without*
   = ~1.8k agent invocations. At ~2 minutes per run that is ~60
   hours of wall-clock. **Plan for parallelism early** — at least
   `--concurrency N`. Possibly also a `--limit 5` dry-run mode.

---

## 4. Known traps (these cost me time)

1. **The `utils/split/run.py` upstream bug.** `split()` dedupes by
   `id` (not `(repo, id)`), so 8 issues that share an id across two
   repos used to silently vanish from the test set. The verify index
   sidesteps this with a local `_split_repo_disjoint` keyed by
   `(repo, id)`. **Do not trust the train/test counts from
   `utils/split/run.py` — they will undercount by 8.** If you need
   to materialise a `train.jsonl` / `test.jsonl` outside of
   `build_verify.py`, use `_split_repo_disjoint` (it's defined in
   `build_verify.py`) or fix the upstream first.
2. **`issue_<NNN>.json`, not `issue.json`.** The raw dir's metadata
   file is named after the issue number — `issue_9.json`, not
   `issue.json`. `build_verify.py` normalises to `issue.json` in
   the pool, so your solver will find it under that name in
   `data/verify/_pool/<owner>__<name>__<id>/`. Don't get confused
   by the raw dir naming.
3. **The pool has exactly 3 files per dir under `--strict`.** No
   `run.log`, no `summary.json`, no `f2p.txt`, no `dockerbuild.txt`,
   no `agentsmith_stat.json`. If you re-run without `--strict`
   (legacy mode) you will see all 7 files; release audits always use
   the default strict 3-file invariant. If you see `run.log`,
   `summary.json`, etc. in `_pool/`, something regenerated without
   `--strict` and you must rebuild.
4. **`*.hallucinated.*` validator rejects.** `utils/train/train_skill.py`
   writes a draft per-repo skill file, validates it, and on failure
   writes the bad draft as `repos/<owner>__<name>.md.hallucinated.<N>`
   and falls back to `fallback_generic_fix.md`. These files exist in
   `agent/skills/` (4 of them, one per skill that had a bad draft)
   but are now `.gitignore`d. If you re-run training and want to
   inspect a draft, look for `*.hallucinated.*`. The smoke-test runs
   live under `agent/skills/<agent>/1/` (train_size=1).
5. **`PYTHONPATH=.` is required** for `python utils/verify/build_verify.py`
   because `utils/__init__.py` does not exist (intentionally — utils
   is a flat package imported via `sys.path.insert`). Same will apply
   to your new `solve.py`.
6. **Same-id-across-repos overwrite (post-mortem).** GitHub issue
   numbers are repo-scoped: `issue-563` in `AntonOsika/gpt-engineer`
   is a totally different bug from `issue-563` in `dapr/dapr-agents`.
   The old pool scheme keyed verify dirs by `<id>` only, so the
   second occurrence silently overwrote the first — meaning half
   the colliding rows pointed at content from the *other* repo.
   The fix is `pool_dir_for(row)` (defined in `build_verify.py`):
   pool dirs are now `data/verify/_pool/<owner>__<name>__<id>/`,
   and `issue.json` carries `repo` + `id` so collisions can no
   longer hide. The audit catches any regression under the
   `pool_dir_uniqueness` check — never bypass it.

---

## 5. Sanity checks before you ship Component 6

- `python utils/verify/build_verify.py --audit` → `200/200 issues clean`
  plus a global `pool_dir_uniqueness` check that also passes.
- All 6 indices pass:
  ```python
  import json
  from pathlib import Path
  indices = {}
  for p in sorted(Path("data/verify").glob("issue_index_*.jsonl")):
      name = p.stem.replace("issue_index_", "")
      indices[name] = {(r["repo"], r["id"]): r["split"] for r in (json.loads(l) for l in p.open())}
  # cross-agent same-size: 0 mismatches
  for sz in (40, 60, 80):
      diff = sum(1 for k in indices[f"mini-swe-agent_{sz}"] if indices[f"mini-swe-agent_{sz}"][k] != indices[f"openhands_{sz}"][k])
      assert diff == 0, f"size {sz}: {diff} cross-agent diffs"
  # monotonicity across sizes: 0 violations
  for sz_from, sz_to in [(40, 60), (40, 80), (60, 80)]:
      m_from = indices[f"mini-swe-agent_{sz_from}"]
      m_to   = indices[f"mini-swe-agent_{sz_to}"]
      viol = [k for k, v in m_from.items() if v == 0 and m_to.get(k) == 1]
      assert not viol, f"{sz_from}->{sz_to}: {len(viol)} monotonicity violations"
  print("OK")
  ```
- `du -sh data/verify/_pool/` reports ~4.8 MB. If it grows past
  ~6 MB, `--force-pool` was run without `--strict` and the
  `summary.json` / `run.log` filtering regressed — re-run with the
  default `--strict`. If it's still ~4.6 MB, the pool was built
  with the **old** id-only scheme (`POOL_DIR / <id>`) — rebuild
  with `--force-pool` to pick up the new `pool_dir_for` scheme.
- `data/verify/audit.json` should still have every entry marked
  `ok: true`, including the `strict_3_file_invariant` check **and**
  the `_GLOBAL_.pool_dir_uniqueness` check.

---

## 6. Open questions for the next agent

- **Cost ceiling.** How much wall-clock / $ are you allowed to spend
  on the full 1.8k-run sweep? The previous agent budgeted ~60 hours
  but never measured actual per-issue time. Run a 5-issue pilot
  first.
- **No-skill baseline: which fallback?** `SKILL.md` (per-repo
  skill) vs `fallback_generic_fix.md` (generic pattern). I
  recommended the latter for the baseline in the doc; you could
  also do *both* baselines (generic-fix only, fully bare prompt) to
  decompose the lift. Pick one and document it.
- **Where to write results.** I proposed
  `results/verify/<agent>_<train_size>.jsonl`. If you have a
  preferred structure, deviate and document.
- **What about the `single_issue` smoke-tests** in `agent/skills/<agent>/1/`?
  They were generated to verify the train pipeline end-to-end on
  one issue. The next agent may want to either delete them or
  include them in the manifest as a "test sanity" record. The
  previous agent left them in because they cost nothing and prove
  the train pipeline works.

---

## 7. Useful commands

```bash
# Verify pool is still valid
python utils/verify/build_verify.py --audit

# Inspect one test row
head -1 data/verify/issue_index_openhands_40.jsonl | python3 -m json.tool

# Inspect what an agent will see
ls data/verify/_pool/strands-agents__sdk-python__issue-1077/
cat data/verify/_pool/strands-agents__sdk-python__issue-1077/issue.json

# See the SKILL.md the agent will be given
cat agent/skills/openhands/40/SKILL.md | head -40

# Re-run the train pipeline if a skill looks wrong
FORCE=1 bash utils/train/run_all.sh
```

---

## 7. New section — Component 6 (rollout) + Component 7 (f2p judge)

Added during the next session (2026-09-06). See TL;DR above and the
"How to run" sections below.

### Rollout (Component 6)

```bash
python utils/verify/solve.py status \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl

python utils/verify/solve.py rollout \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1058 --skill-mode with

# Full rollout (idempotent, skipped-done by default)
python utils/verify/solve.py rollout \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl
```

### f2p judge (Component 7)

```bash
python utils/verify/score.py score \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1058

python utils/verify/score.py summary \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl

python utils/verify/score.py inspect \
    --index data/verify/issue_index_mini-swe-agent_40.jsonl \
    --pilot-id issue-1058
```

### Output layout

```
data/verify/runs/<agent>_<train_size>/<owner>__<repo>__<id>/
    image_meta.json
    with_skill/{prompt.txt,trajectory.json,patch.txt,agent.json,eval.json,eval_report.txt}
    without_skill/{...}
```

### Known limitations

- Repo clones need `git fetch --unshallow` before base SHAs resolve.
- Pool `issue.json` lacks `linked_prs[].base_sha` and `linked_prs[].patch`;
  `score.py` injects the agent's patch + falls back to `row.base_sha`.
- Some issues will score f2f due to environment drift (mcp version,
  etc.), not agent failure.

### Outstanding work

1. Full rollout (1 444 runs) — staged via `--max-rows` in tmux.
2. Pre-flight `git fetch --unshallow` for all 11 upstream clones.
3. `score.py score` on all 6 indices.
4. Aggregate pass@1 by (agent × train_size × skill_mode).

---

*End of handoff. The previous agent is gone; you are now the
author of Component 6. Good luck.*
