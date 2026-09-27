# MLE-Agent Issue Fixing Notes

## Repo identity

The `MLE-Agent` repository is designed to be your intelligent companion for seamless AI engineering and research. It features an agent to automate your MLE processes, leveraging Python as its primary language.

## Typical issue shape

- Common issues include bug reports, feature requests, and regressions.
- Reports are usually well-specified and often come with clear reproduction steps.
- The issue labels help in categorizing and prioritizing the bugs and feature requests.

## Recurring fix patterns

- When you see **a failure in the `mle` operations**, the fix is usually in `mle/utils/system.py` to ensure proper dependencies are loaded.
- When facing **model integration issues**, inspect `mle/integration/github.py` for any missing API calls or incorrect dependencies.
- For **functionality bugs occurring in the `debugger` class**, a typical fix can often be found in `mle/agents/debugger.py`, especially focusing on method parameter handling.

## Files / modules that change most often

| Path                                     | Reason for frequent change                       |
|------------------------------------------|------------------------------------------------|
| `src/mle/agents/`                        | Updates to agent logic and new functionalities  |
| `src/mle/integration/`                  | Changes in integration APIs for external services|
| `src/tests/`                             | Continuous addition of tests for new features   |
| `src/mle/utils/`                        | Utility functions are frequently updated        |

## Pitfalls

- Forgetting to **update the test cases** in `tests/test_litellm_model.py` can lead to passing builds despite broken functionality.
- Be cautious of **async/sync mismatch scenarios** in agent functions, which might not throw immediate errors but can lead to runtime issues.
- Overlooking the need to **validate inputs** can lead to unhandled exceptions during execution.

## Test conventions

Tests are located in the `src/tests/` directory. They are invoked using Python test runners like `pytest`. It's common to name the test files following the convention `test_<module_name>_<description>.py`, providing clarity on what each test covers.

## One concrete worked example

**Issue 7**: This issue was related to improper handling of API calls within the `kaggle.py` module. The fix involved updating the error handling in the relevant function to ensure more robust interaction with the Kaggle API. The linked pull request can be found in **PR #44**.
