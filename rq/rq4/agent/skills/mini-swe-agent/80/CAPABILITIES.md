# Capability → F2P link

The five scanners in `scripts/` are **generic**. They were distilled
from held-out issues whose raw AgentBug-Smith artifacts already had
a gold fail-to-pass test, but a skill-less / notes-only agent did
**not** produce a passing patch (`no_patch`, `f2f`, or
`catastrophic_patch`).

Once the matching capability is applied as a **small, compiling
edit**, those same original issues become stable F2P. The table is
the evidence; the scripts do not hard-code issue numbers.

Source artifacts (issue body, fail vs f2p runs, gold patch) live under
`RQ4/incremental/increment/issue_<N>/`.

| Capability | Script | Original issue | Symptom without the capability | Stable edit the script points at |
|---|---|---|---|---|
| **C1** `C_widen_match` | `widen_match.py` | [harness-sdk#1705](https://github.com/strands-agents/harness-sdk/issues/1705) | `_supports_caching` is ` "claude" in id or "anthropic" in id`. Application inference-profile ARNs contain neither token, so caching stays off. Agent either no-patches or rewrites the whole model file. | Widen the `in` predicate (or add an `anthropic` strategy) so an ARN / profile id is recognized. Gold PR [1808](https://github.com/strands-agents/harness-sdk/pull/1808), `src/strands/models/bedrock.py`. |
| **C2** `C_normalize_empty` | `guard_empty.py` | [harness-sdk#2122](https://github.com/strands-agents/harness-sdk/issues/2122) | Formatter loops `toolResult.content` and forwards `[]`. Strict providers reject the payload. Without the empty-guard hint the agent edits the wrong helper or skips the format boundary. | Before the loop: `if not content: content = [{"text": ""}]`. Gold PR [2123](https://github.com/strands-agents/harness-sdk/pull/2123), `_format_bedrock_messages` / `_format_request`. |
| **C3** `C_fallback_path` | `fallback_loop.py` | [harness-sdk#2173](https://github.com/strands-agents/harness-sdk/issues/2173) | `reduce_context` walks messages, skips every trim point, then `for`/`else` raises `Unable to trim conversation context!`. Tool-heavy threads have no primary cut. Agents that only tighten the primary filter stay `f2f`. | In the `else`, try a more lenient boundary (e.g. a complete toolUse+toolResult pair) **before** raising. Gold PR [2174](https://github.com/strands-agents/harness-sdk/pull/2174). |
| **C4** `C_boundary_zero` | `boundary.py` | [harness-sdk#2205](https://github.com/strands-agents/harness-sdk/issues/2205) | `trim_index = len(messages) - window_size`. For `window_size=0` the while-loop condition is immediately false, so messages are left unchanged. Agents change the default or the warning and still fail the `== []` assert. | `window_size < 0` → `ValueError`; `window_size == 0` → `messages.clear()` and return. Gold PR [2208](https://github.com/strands-agents/harness-sdk/pull/2208). |
| **C5** `C_plumb_arg` | `plumb.py` | [harness-sdk#362](https://github.com/strands-agents/harness-sdk/issues/362) | `Agent.structured_output` has `self.system_prompt` but calls `model.structured_output(model, messages)` without it. Tests assert the inner call received the prompt. Agents add caching logic or edit Bedrock instead of the one keyword. | `model.structured_output(..., system_prompt=self.system_prompt)`. Gold PR [466](https://github.com/strands-agents/harness-sdk/pull/466), `src/strands/agent/agent.py`. |

## How to read this as a causal link

```
original issue.json + f2p test
        │
        ▼
 localize.py  ── file the test actually imports
        │
        ▼
 scan.py      ── one of C1–C5, with file:line and a one-line edit
        │
        ▼
 edit.py + verify.py compile + verify.py f2p
        │
        ▼
 guard_patch.py  ── blocks the failure modes that used to dominate
                    (no_patch, IndentationError, catastrophic rewrite)
        │
        ▼
 F2P  (rc_base != 0, rc_patched == 0)
```

`guard_patch.py` is the negative capability: it does not create F2P
by itself, but it stops the three outcomes that previously ate the
same five issues (`agent_failed`, `catastrophic_patch`, collection
`ERROR` counted as `f2f`).

## What is intentionally *not* in the scripts

- No hard-coded path `src/strands/...`
- No issue numbers in the scanners
- No gold-patch text
- No per-repo "if Bedrock then …" branch

If a new issue exhibits the same *shape* (narrow `in` check, empty
list at an API boundary, for/else raise, `len-n` with `n=0`, dropped
keyword), the same script should fire. That is the generalization
these five originals bought.
