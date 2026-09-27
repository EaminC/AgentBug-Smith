# Repo identity

The `strands-agents/sdk-python` repository implements a model-driven approach to building AI agents in just a few lines of code. It provides shared Python tooling for the Strands monorepo. Maintained by the Strands team, this repository includes key subdirectories such as `strands-mcp/`, `strands-py/`, `strands-ts/`, and `test-infra/`, where the core code lives.

# Typical issue shape
- Issues typically include bug reports, enhancement requests, and regressions.
- The repro steps for bugs are often well-defined, usually requiring users to provide details about inputs and expected behavior.
- Commonly, issues link to pull requests which may detail proposed fixes or improvements.
- Feature requests are often less specific and may require further discussion to clarify expectations.

# Recurring fix patterns
- When you see an issue related to incorrect agent behavior, the fix is usually implementing additional validation in `src/strands/agent/agent.py`.
- If a test fails due to a missing parameter, the fix often requires modifying the function signature in `src/strands/agent/hooks.py`.
- When encountering missing packages, the resolution typically involves adding the relevant requirements in `pyproject.toml` or similar dependency files.
- If asynchronous behavior is broken, adjust the async handling in `src/strands/async_handler.py` according to the latest standards.
- When there's a regression related to agent commands, it's common to refactor the command handler in `src/strands/commands.py`.

# Files / modules that change most often
| Path                       | Why it gets touched                 |
|----------------------------|-------------------------------------|
| `src/strands/agent/agent.py`   | Core agent functionalities            |
| `src/strands/commands.py`        | Command handling logic               |
| `src/strands/async_handler.py`   | Async operations and flow            |
| `pyproject.toml`                | Dependency updates                   |

# Pitfalls
- Forgetting to update `pyproject.toml` with new dependencies can lead to runtime errors.
- Assuming all functions are synchronous can cause issues with async calls.
- Overlooking input validations may lead to errors that aren't immediately evident.
- Not updating the linked tests after making changes can cause CI/CD failures.

# Test conventions
Tests are stored under the `test-infra/` directory. They are typically named using the format `test_<issue_number>.py`. To run the tests, use `pytest` from the project root.

# One concrete worked example
**Issue #45: Incorrect response handling in agent commands**. This issue was resolved by refining the command parsing logic in `src/strands/commands.py`. The PR that addressed this can be found [here](https://github.com/strands-agents/sdk-python/pull/45).