---
name: rq4-issue-fixer
description: Generic Python issue-fixer with runtime scanners plus per-repo notes from 80 training issues. Scripts localize a failing test, scan five reusable fix capabilities, apply a surgical edit, then verify compile + f2p. Use when fixing a GitHub issue in a Python repo (especially agent-framework repos: strands-agents, agentscope, crewAI, MLE-agent, gpt-engineer, aider, langgraph, dapr-agents, AutoGPT, open-interpreter, sdk-python) with tests under tests/.
---

# RQ4 Issue Fixer

This skill is a **set of runtime scripts**, not a list of memorized
repo patterns. Per-repo notes in `repos/` are optional hints only.

Scripts live at `/skill/scripts` when the harness mounts them, or at
`scripts/` next to this file. Run them with `python3 <that-dir>/...`.

## When to use

Use this skill when the user:

- pastes a GitHub issue link or text describing a bug / feature
  request in one of the 11 supported repos, OR
- asks "fix this issue", "reproduce and patch", or "follow the
  pattern used in the linked PR".

Do **not** use for:

- Pure refactors, doc updates, or test-only changes (the training
  data is biased toward bug fixes and feature additions).
- Issues whose title is short and vague with no body — load the
  per-repo notes first to see if that repo's issues are typically
  well-specified.

## Workflow (do this in order)

```
1. localize.py   → which source file
2. scan.py       → which capability, which line
3. edit.py       → one surgical replace/insert
4. verify.py     → py_compile then f2p
5. guard_patch.py → reject catastrophic / rename / docstring inserts
```

```bash
SCRIPTS=/skill/scripts   # fallback: scripts/
python3 $SCRIPTS/localize.py --test tests/<TEST>.py --src src/ --issue issue.json
python3 $SCRIPTS/scan.py     --src src/ --test tests/<TEST>.py --issue issue.json
python3 $SCRIPTS/edit.py replace --file <FILE> --old '<OLD>' --new '<NEW>'
python3 $SCRIPTS/verify.py compile --file <FILE>
python3 $SCRIPTS/verify.py f2p --test tests/<TEST>.py
git diff > /tmp/final.patch
python3 $SCRIPTS/guard_patch.py --patch /tmp/final.patch --file <FILE>
```

Stop after the first high-confidence `scan.py` hit that matches the
failing assertion. One capability per attempt.

## The five capabilities (and why they unlock F2P)

These are generic AST scanners. They do not mention any one repo.
Each one exists because a held-out issue **failed without it**
(`no_patch` / `f2f` / catastrophic rewrite) and **became F2P once
the agent applied that capability surgically**.

Full mapping: [CAPABILITIES.md](CAPABILITIES.md)

| ID | Capability | Script | What it finds | What you edit |
|----|------------|--------|---------------|---------------|
| C1 | widen a too-narrow identifier check | `widen_match.py` | `return "a" in s or "b" in s` that misses an ARN/alias token from the issue | add the missing token or an alternate lookup |
| C2 | normalize an empty payload field | `guard_empty.py` | loop / pass-through of `content` (or similar) with no `if not field` | insert a one-element placeholder before the API call |
| C3 | add a fallback when a skip-loop finds nothing | `fallback_loop.py` | `for`/`else` that raises "unable to…" | run a more lenient cut **before** the raise |
| C4 | handle size/window `== 0` | `boundary.py` | `len(x) - n` with no `n==0` / `n<0` guard | reject negatives; `n==0` clears / early-returns |
| C5 | plumb a missing keyword | `plumb.py` | `inner(...)` omits `foo=` even though `self.foo` exists and the issue says it is not passed | add `foo=self.foo` |

## Rules that keep patches F2P-grade

1. **Localize once.** `localize.py` plus the test's first import is
   almost always the right file. Do not wander into a re-export.
2. **Edit must compile.** `edit.py` and `verify.py compile` gate on
   `py_compile`. A SyntaxError / IndentationError is an automatic
   `f2f` (collection error).
3. **Stay surgical.** `guard_patch.py` rejects `+80` / `-30` and
   public renames. Those correlate with non-F2P outcomes.
4. **Do not insert inside a docstring.** If `edit.py` can't find
   `--old`, re-read the exact bytes — do not guess an indent.
5. **Do not invent a second file** unless `scan.py` hits it with
   `confidence=high`.

## What does NOT work

- Catastrophic rewrites of a whole module
- Renaming public classes / methods the test already imports
- Patching `strands-py/` or `strands-ts/` when the installable
  package is `src/<pkg>`
- Submitting without `verify.py f2p`

## Optional per-repo notes

If `repos/<owner>__<name>.md` exists, skim it **after** `scan.py`.
Each notes file contains:

- The repo's typical issue shape (well-specified bug vs. feature
  request vs. regression report).
- Recurring failure modes and their idiomatic fix patterns.
- File paths and modules that most often need changing.
- Common pitfalls (e.g. test fixtures, async/sync boundaries).

If it is missing, use [fallback_generic_fix.md](fallback_generic_fix.md)
only as a reading-order hint — never as a substitute for the scanners.

## Provenance

This skill was generated from 80 training issues across 3 repos,
see `manifest.json`. The training split used
`mode = repo_disjoint`, so any repo whose notes are present here is
*fully* in the training set; the skill has not seen test issues
from those repos at evaluation time.

The five scanners were distilled separately: held-out issues that
failed without the matching capability and became F2P after a
surgical application. Scanners do not hard-code those issue ids.

## Refresh

Re-run `python utils/train/train_skill.py --agent <this-agent>
--train-size <this-size>` to rebuild this skill. Existing
`repos/*.md` files are reused unless `--force` is passed.
