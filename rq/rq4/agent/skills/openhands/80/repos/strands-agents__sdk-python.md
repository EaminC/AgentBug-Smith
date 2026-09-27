# Strands Agents SDK Python Fixing Guide

## Repo identity
This repository is a model-driven approach to building AI agents in just a few lines of code. The project is named `strands-monorepo-tools` and provides shared Python tooling for the Strands monorepo. It is not published and includes several top-level subdirectories under `src/`: `strands-mcp/`, `strands-py/`, `strands-ts/`, and `test-infra/`.

## Typical issue shape
- Issues often contain bug reports related to AI agent functionalities and exception handling.
- Feature requests for enhancements or expansions of existing modules are also present.
- Issues include reproduction steps often provided in Python code snippets.
- Typically, users confirm they are on the latest version of the Strands software.
- Common labels are "bug" and "ready for contribution".

## Recurring fix patterns
- **When you see** `ContextWindowExceededError`, **the fix is usually** to catch it and raise a `ContextWindowOverflowException` in `strands-py/src/strands/models/litellm.py`.
- **When you see** inconsistent exception handling for agent errors, **the fix is usually** to standardize exception mapping as done in the `test_litellm.py`.
- **When you see** an input that exceeds the model’s context window, **the fix is usually** to test with oversized inputs in `strands-py/tests/strands/models/test_litellm.py` to ensure the proper exception is raised.
- **When you see** failure in `async` agent calls, **the fix is usually** to ensure proper context handling in the model invocation.

## Files / modules that change most often
| Path                              | Why it gets touched                                     |
|-----------------------------------|--------------------------------------------------------|
| `strands-py/src/strands/models/litellm.py`  | Frequently updated to manage exceptions for LLM calls. |
| `strands-py/tests/strands/models/test_litellm.py` | Modified to keep tests aligned with agent behavior. |

## Pitfalls
- **Forgetting to update exception handling**: Ensure that new exception types introduced by models are accounted for.
- **Not running the full test suite**: Skipping tests can lead to undetected bugs, particularly in edge cases.
- **Assuming synchronous behavior in async calls**: Make sure that all calls expected to yield responses are correctly awaited.

## Test conventions
Tests for this repository reside in the `tests/` directory. They are typically invoked using `pytest`, with naming conventions such as `test_<component>.py` to indicate their purpose. Tests should ensure that all functionalities adhere to expected behaviors before a PR is submitted.

## One concrete worked example
Issue [#974](https://github.com/strands-agents/sdk-python/issues/974): This issue involved the `LiteLLM Model` not throwing the expected `ContextWindowOverflowException` when input exceeded its limit. The fix was successfully merged in PR [#994](https://github.com/strands-agents/sdk-python/pull/994), which mapped `LiteLLM` context window errors to the expected exception for more reliable input handling.