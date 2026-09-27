# Repo Identity

The `strands-agents/sdk-python` repository is designed for building AI agents using a model-driven approach. It contains a Python SDK and TypeScript SDK under the repository name `strands-monorepo-tools`. The framework is maintained by the Strands team and facilitates the development and running of AI agents efficiently. The repository is not published and serves as a shared Python tooling framework for the Strands monorepo.

## Typical Issue Shape
- Issues are primarily bug reports and feature requests.
- Issues often include clear reproduction steps, specific environment details, expected and actual behavior.
- There is an issue template confirming the steps for reproduction and checks for relevant updates.

## Recurring Fix Patterns
- When you see a context overflow issue in `strands.models.litellm`, the fix is usually to map the `ContextWindowExceededError` to `ContextWindowOverflowException` by modifying `strands-py/src/strands/models/litellm.py`.
- When `LiteLLMModel` fails to catch specific exceptions, ensure that the errors are raised correctly using `try/except` blocks to wrap model invocations in `strands-py/src/strands/models/litellm.py`.
- To update structured output mappings, check for instances where the model's support for response schemas is patched in `strands-py/src/strands/models/litellm.py`.
- For tests related to exceptions, examine `strands-py/tests/strands/models/test_litellm.py` for appropriate patterns when simulating exceptions.

## Files / Modules That Change Most Often
| Path                                   | Reason for Changes                              |
|----------------------------------------|------------------------------------------------|
| `strands-py/src/strands/models/litellm.py`       | Resolving exceptions and handling model errors. |
| `strands-py/tests/strands/models/test_litellm.py`| Adding or updating tests related to error handling. |

## Pitfalls
- Forgetting to catch exceptions that the model might raise can lead to unhandled errors in agent behavior.
- Not updating the test cases corresponding to code changes can result in missing coverage of new functionalities or fixes.
- Overlooking changes in the API contract from external model providers might lead to regression failures.

## Test Conventions
Tests are located within the `tests/` directory, structured and named according to functionality. For instance, many tests use the naming convention `test_*.py`, often containing asynchronous testing with `pytest.mark.asyncio` to handle async operations effectively.

## Worked Example
For Issue [#974](https://github.com/strands-agents/sdk-python/issues/974): The issue involved the `LiteLLM Model` not throwing a `ContextWindowOverflowException` on exceeding the context window. The related pull request [#994](https://github.com/strands-agents/sdk-python/pull/994) provided the necessary fixes by updating the exception handling in `strands-py/src/strands/models/litellm.py` to ensure that it raises the correct exceptions for input lengths that exceed model constraints. This was validated by augmenting the test suite in `strands-py/tests/strands/models/test_litellm.py` to check for the correct exception handling behavior after applying the patch.