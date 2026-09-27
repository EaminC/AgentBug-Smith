# Smoke test — 1 issue, 2 agents, 2 skills

## What this is

A reproducible end-to-end check of the training pipeline using the
smallest possible input: a single closed issue. It exercises:

- `utils/train/train_skill.py --single-issue`
- the per-repo scratch + clone + materialisation
- the agent invocation (`agent/run_mini.sh` and `agent/run_openhands.sh`)
- the SKILL.md / repos/*.md / fallback / manifest finalisation

## Issue used

`issue-974` in `strands-agents/sdk-python` — a single-issue repo, so
this is also the only repo the smoke test touches. The issue is a
bug report: LiteLLMModel does not throw ContextWindowOverflowException
when the context window is exceeded. The golden patch is missing from
the data dir, so `fail2pass_test.py` and `issue.json` are the only
inputs the agent has to work from.

## How to reproduce

```bash
# mini-swe-agent
agent/.venv/bin/python utils/train/train_skill.py \
  --agent mini-swe-agent \
  --train-size 1 \
  --single-issue issue-974 \
  --single-repo strands-agents/sdk-python \
  --out /tmp/rq4-smoke-mini \
  --scratch-root /tmp/rq4-smoke-mini/scratch \
  --cost-limit 2.0

# openhands
agent/.venv/bin/python utils/train/train_skill.py \
  --agent openhands \
  --train-size 1 \
  --single-issue issue-974 \
  --single-repo strands-agents/sdk-python \
  --out /tmp/rq4-smoke-oh \
  --scratch-root /tmp/rq4-smoke-oh/scratch \
  --cost-limit 2.0
```

Note: `--single-issue` requires `--single-repo` because issue ids are
NOT unique across repos (verified: `issue-974` exists in both
`agentscope-ai/agentscope` and `strands-agents/sdk-python`).

## Output layout (both runs produce identical structure)

```
/tmp/rq4-smoke-<agent>/
└── <agent>/1/
    ├── SKILL.md                       # from template
    ├── fallback_generic_fix.md        # from template
    ├── manifest.json                  # with smoke_test: true
    └── repos/
        └── strands-agents__sdk-python.md   # written by the agent
```

## Findings from this run (committed to docs/)

**mini-swe-agent** (~30s, 2154 bytes notes):

- Correctly identifies the repo, exception class, and target file
  `src/strands/models/litellm.py`.
- Style matches the prompt template (the 7 sections are all present).
- Issue is correctly summarised with the right issue id and link.

**openhands** (~3min, 3787 bytes notes):

- Produced a file in the right shape and at the right path.
- **Quality is poor**:
  - Mis-identifies the repo as "OpenHands Software Agent SDK for
    mobile robot applications".
  - Invents fake file paths (`src/strands/navigation/navigation.py`,
    `src/strands/state/state_manager.py`, `src/strands/async_utils.py`)
    that don't exist in the upstream repo.
  - References a non-existent "issue #42" and "PR #60".
  - Generic LLM-fluff in the "recurring fix patterns" section
    instead of the actual `ContextWindowOverflowException` pattern.
- Hypothesis: either the agent ran out of cost budget and produced a
  hallucinated answer, or it didn't fully read the scratch input.

## What this tells us

1. The pipeline plumbing works end-to-end — materialisation, prompt
   assembly, agent invocation, output bundling, manifest writing.
2. Skill quality is **highly sensitive to the agent's grounding**.
   The same prompt produces a faithful skill on mini-swe-agent and a
   hallucinated skill on openhands. This validates that the
   downstream Component 4 (evaluator) needs to test both agents on
   the same skills, because the skill-by-itself is not the variable
   that determines quality — it's the (skill, agent) pair.
3. **Action item for openhands run**: either give it more cost
   budget, or simplify the prompt so it can't drift into
   hallucination. A follow-up will tighten the prompt with
   "do not invent file paths you haven't `ls`-verified" and bump
   the openhands cost limit to 5.0.
