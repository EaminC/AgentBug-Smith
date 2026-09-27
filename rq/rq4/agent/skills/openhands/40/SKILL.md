---
name: rq4-issue-fixer
description: Use this skill when the user asks to fix a GitHub issue in an agent-framework repository (strands-agents, agentscope, crewAI, MLE-agent, gpt-engineer, aider, langgraph, dapr-agents, AutoGPT, open-interpreter, sdk-python). The skill encodes per-repo fix idioms distilled from 200 closed issues. Do not use for issues outside this repo set, or for non-fix tasks (refactors, docs, tests-only).
---

# RQ4 Issue Fixer

A patch-distillation skill. It teaches the agent how **closed issues
in agent-framework repos were fixed**, so it can apply the same
patterns to new issues in those repos.

## When to use

Use this skill when the user:

- pastes a GitHub issue link or text describing a bug / feature
  request in one of the 11 supported repos, OR
- asks "fix this issue", "reproduce and patch", or "follow the
  pattern used in the linked PR".

Do **not** use for:

- Issues in unrelated repos (the per-repo notes in `repos/` will
  mislead the agent).
- Pure refactors, doc updates, or test-only changes (the training
  data is biased toward bug fixes and feature additions).
- Issues whose title is short and vague with no body — load the
  per-repo notes first to see if that repo's issues are typically
  well-specified.

## Per-repo notes

Load the relevant repo's notes via `@repos/<owner>__<name>.md` once
the issue's repo is identified. Each notes file contains:

- The repo's typical issue shape (well-specified bug vs. feature
  request vs. regression report).
- Recurring failure modes and their idiomatic fix patterns.
- File paths and modules that most often need changing.
- Common pitfalls (e.g. test fixtures, async/sync boundaries).

If `@repos/<owner>__<name>.md` is missing, fall back to
`@fallback_generic_fix.md` (if present) and tell the user the repo
is not in the trained set.

## How to fix a new issue using this skill

1. **Identify the repo** from the issue body or the user's message.
2. **Load the repo notes** with `@repos/<owner>__<name>.md`.
3. **Reproduce** — read the existing tests, run the failing test
   the issue references, capture the traceback or wrong output.
4. **Localize** — grep for the symptoms (error message, function
   name, failing assertion) to find the source module.
5. **Patch** following the patterns in the repo notes; preserve
   the test surface so existing f2p tests stay green.
6. **Verify** — run the failing test, then a wider unit-test slice
   to catch regressions.

## Provenance

This skill was generated from 40 training issues across 1 repos,
see `manifest.json`. The training split used
`mode = repo_disjoint`, so any repo whose notes are present here is
*fully* in the training set; the skill has not seen test issues
from those repos at evaluation time.

## Refresh

Re-run `python utils/train/train_skill.py --agent <this-agent>
--train-size <this-size>` to rebuild this skill. Existing
`repos/*.md` files are reused unless `--force` is passed.
