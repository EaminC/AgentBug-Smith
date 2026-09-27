# Generic Fallback — when the repo is not in the trained set

If the user's issue is in a repo not covered by `repos/`, fall back
to a generic agent-framework issue-fixing recipe.

## Generic recipe

1. **Read the issue body** end-to-end. Identify:
   - the symptom (error message, wrong behaviour, missing feature)
   - the proposed solution (often a PR link is provided)
   - any "alternatives considered" (these hint at non-obvious
     constraints)
2. **Check the issue's labels** — `bug`, `enhancement`, `good first
   issue`, `paper cut`, etc. The label usually tells you how
   surgical the patch should be.
3. **Find the relevant module** by grepping for the symptom string,
   the error class, or the proposed fix path. The fix almost
   always lives in `src/<package>/...`.
4. **Match the repo's test layout** — most agent frameworks put
   unit tests in `tests/unit/` and integration tests in
   `tests/integration/`. New behaviour needs unit coverage;
   behavioural fixes need a regression test.
5. **Patch conservatively**:
   - Match the surrounding code style (line length, import order,
     type hints).
   - Don't refactor unrelated code, even if it bothers you.
   - Update docstrings only if behaviour changed.
6. **Run the smallest reasonable test subset** first, then expand
   if it passes.
7. **If the issue links a PR**, read that PR's diff (not just its
   description) — it is the ground truth for the maintainer's
   preferred fix shape.

## When to ask the user for clarification

- The issue body is empty or one-liner: ask for the steps to
  reproduce or the expected vs. actual behaviour.
- The issue touches multiple subsystems: ask which subsystem to
  prioritize.
- The issue is a feature request: confirm the user wants the
  feature implemented (vs. just a design discussion).
