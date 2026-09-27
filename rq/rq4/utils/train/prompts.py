"""Prompts assembled by utils.train.train_skill.

These strings are sent to the per-repo agent (mini-swe-agent or
openhands) as the task description. They tell the agent exactly:

- which repo to clone, where to put it
- which issues to read, where the patches are
- what to write, where to write it, in what shape
- how to make the output composable with other repos' notes

Keep prompts deterministic (no f-string time / randomness) so they
re-render identically across runs.
"""
from __future__ import annotations

from pathlib import Path


REPO_NOTES_INSTRUCTIONS = """\
You are writing one file of a multi-file Cursor Agent Skill called
`rq4-issue-fixer`. The skill teaches an agent how to fix issues in
the repository **{repo}**:

Your output is a single markdown notes file. It will be loaded by the
agent on demand (via `@repos/{safe_repo}.md`) when a new issue in
this repo needs fixing. Treat this as **training data for a
downstream agent**, not as a human report.

## Repo identity (canonical, from the upstream repo)

{description_block}

The above description was extracted from the upstream repo's own
README / pyproject. **Treat it as ground truth.** Do not override
it with your prior beliefs about what the repo "probably" is.

## ⚠️ Grounding rules (HARD CONSTRAINTS — read first)

A post-write validator checks your output for hallucinations. If it
flags anything, the run is rejected and you waste a costly retry. So:

1. **Every claim must come from something you actually read.** Before
   writing each section, `cat` or `read` the relevant input file
   (`issue.json`, `patch.diff`, `fail2pass_test.py`, `src/README.md`,
   `src/pyproject.toml`, etc.). Do not paraphrase LLM priors about
   what the repo "probably" does.

2. **Every file path, function name, class name you mention must
   literally appear in one of the inputs.** The validator greps
   your output against paths found in `src/` and names found in
   `issue.json` / `patch.diff`. Made-up paths fail the check.

3. **Every issue number / PR link you cite must come from
   `issue.json` or `patch.diff`.** Do not invent issue numbers,
   even round ones. If no concrete issue is to be cited, write
   `Issue <id-from-issue.json>: <title from issue.json>` — copy
   the title verbatim.

4. **If the inputs say "AI agent SDK", that is what you write** —
   even if the name makes you think of something physical. The
   description block above is canonical.

5. **Quote 1-2 short snippets (3-10 lines) verbatim from a real
   `patch.diff` if you want to illustrate a pattern.** If no
   patch.diff exists for any issue, omit the snippet rather than
   inventing one.

## ⚠️ Tool invocation rules (HARD CONSTRAINTS — read first)

You will write the markdown notes file. There are three workable
methods, in order of preference:

**Method 1 (preferred): one short `file_editor` call with all
required fields.** The OpenHands `file_editor` tool requires every
call to include `security_risk` and `summary` fields. The model
has been observed to forget these on long prompts. If you forget
them, **the call is silently rejected and no file is written**.

When calling `file_editor` you MUST include both fields:

    file_editor(command="create", path="<path>",
                file_text="<full markdown>",
                security_risk="LOW",
                summary="Write skill notes for <repo>")

**Method 2 (if file_editor keeps rejecting):** the `terminal` tool
with a single short command that completes in well under 30
seconds (the terminal tool times out on heredocs because they
produce no stdout). Use a chain like:

    : > '<path>'
    python3 -c "open('<path>','w').write(__import__('base64').b64decode('<BASE64>').decode())"

Encode the entire markdown as base64 in the python command. Each
line is short, no heredoc, no 30-second timeout.

**Method 3 (last resort):** just print the full markdown as your
final assistant message text (NOT inside a code block, NOT as a
tool call — just as plain message content). The orchestrator will
read your message and save it to disk. If you go this route, send
ONE message with the complete markdown and then call the `finish`
tool.

You may use `file_editor` for READING files (`view`,
`str_replace` mode) freely.

## Input you will receive

The orchestrator has already cloned `{repo}` into a scratch
workspace at `{scratch_dir}`. Inside that workspace you will find:

- The full upstream source tree of `{repo}` — read it freely.
- One folder per closed issue:
  `{scratch_dir}/issues/<issue_id>/`
  containing (some of which may be absent):
    - `issue.json`         — original GitHub issue body, labels,
                             linked PRs.
    - `patch.diff`         — the f2p-tested golden patch that fixed
                             the issue. **May be absent** — the
                             dataset does not always carry it. If you
                             see `PATCH_MISSING.txt` instead, distill
                             the fix from the issue body + failing
                             test + surrounding code.
    - `fail2pass_test.py`  — the test that was failing before the
                             patch and passing after. Read this to
                             understand the contract the fix has to
                             satisfy.
    - `f2p.txt`            — the fail-to-pass test trace / stdout.
    - `summary.json`       — provenance and pass/fail status.
    - `run.log`            — full agent run log (if present).
    - `env.dockerfile`     — the test environment (if present).
    - `agentsmith_stat.json` — token / cost / time stats for the
                             original run (if present).

These issues span the **whole** repo (train + test split from the
research perspective — that doesn't matter for you, you are
distilling the repo's fix idioms, not learning the split).

## What to write

Write exactly one file at:

  {out_path}

The file should be **markdown, 80-300 lines**, with these sections:

1. **Repo identity** — one paragraph: what the repo does, the
   language/framework, who maintains it.

2. **Typical issue shape** — 3-5 bullets. What kinds of issues
   appear here (bug reports, feature requests, regressions)?
   How well-specified are they? Is there a "bug template" that
   gives reproduction steps?

3. **Recurring fix patterns** — 3-7 bullets, each in the form
       "When you see X, the fix is usually Y in <module>".
   Concrete module paths, function names, class names. These are
   the highest-leverage lines — they let the downstream agent
   pattern-match new issues quickly.

4. **Files / modules that change most often** — table of
       `<path> | <why it gets touched>`.

5. **Pitfalls** — 3-5 bullets. Things that look like a fix but
   aren't (e.g. forgetting to update a registry, async/sync
   mismatch, breaking the tool-call schema).

6. **Test conventions** — 1 paragraph. Where tests live, how they
   are invoked, naming conventions (e.g. `test_<issue_number>.py`).

7. **One concrete worked example** — pick one issue from the
   inputs (any one), summarise it in 4-6 lines, link to the issue
   id and the PR if the issue JSON gives one.

## Style

- Use backticks for all file paths, function names, class names.
- Prefer concrete over abstract. "Edit `src/strands/agent/agent.py`
  line 612 to pass `messages` to the hook" beats "the agent
  invocation flow needs improvement".
- Quote 1-2 short snippets (3-10 lines) from a real patch.diff if
  they illustrate a recurring pattern.
- Do not invent behaviour you didn't observe in the inputs.

## What NOT to do

- Don't write code in the notes file — only describe patterns.
- Don't paste full patch.diff bodies — distill them.
- Don't add sections like "Conclusion" or "Further work" — this
  is a reference doc, not an essay.
- Don't reference the orchestrator, the scratch dir, or the
  training pipeline by name. The downstream agent should treat
  this as if it were written by hand.

When the file is written, send a final brief assistant message
("Wrote <path>") and stop. (If file_editor kept rejecting your
calls, your final plain-text message itself may be the
markdown — the orchestrator will pick it up.)
"""


def repo_lessons_prompt(
    repo: str,
    description: str,
    description_block: str,
    scratch_dir: str,
    out_path: str,
    issue_titles: list[str] | None = None,
) -> str:
    """Build the per-repo training prompt.

    ``description`` is kept for backward compat but ``description_block``
    is the canonical content shown to the agent. It should already
    contain the repo's purpose + language + identity, in plain
    markdown, with at most ~10 lines. If the caller could not extract
    a description, ``description_block`` should be a literal
    ``"(no description extracted)"`` placeholder.

    ``issue_titles`` is a list of real issue titles from the input
    dataset; when present they are embedded verbatim in the
    prompt so the agent's worked-example section has a real
    reference to quote.
    """
    safe_repo = repo.replace("/", "__")
    issue_block = ""
    if issue_titles:
        issue_block = (
            "\n## Issue titles available in this scratch\n"
            "Quote one of these verbatim in your worked-example "
            "section (the validator checks for it):\n\n"
            + "\n".join(f"- {t}" for t in issue_titles[:5])
            + "\n"
        )
    return REPO_NOTES_INSTRUCTIONS.format(
        repo=repo,
        description=description,
        description_block=description_block,
        safe_repo=safe_repo,
        scratch_dir=scratch_dir,
        out_path=out_path,
    ) + issue_block


def safe_repo_name(repo: str) -> str:
    """Map 'owner/name' to a filename-safe slug."""
    return repo.replace("/", "__").replace(" ", "_")


def issue_id_from_path(p: Path) -> str:
    """Extract the issue id from a data/raw/... issue directory.

    Directory layout: ``issue_<id>_<timestamp>`` → returns ``<id>``.
    """
    name = p.name
    if name.startswith("issue_"):
        parts = name.split("_")
        # 'issue_<digits>_<timestamp>' → take parts[1]
        return parts[1] if len(parts) >= 2 and parts[1].isdigit() else name
    return name
