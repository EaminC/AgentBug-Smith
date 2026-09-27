# Repo Identity
This repository, `strands-agents/sdk-python`, is focused on building AI agents primarily using Python. It facilitates interaction with various models and tools within the Strands monorepo framework. Maintained by the Strands team, the project aims to streamline the development of AI agents through a model-driven approach.

# Typical Issue Shape
- **Bug Reports**: Users report issues encountered while using the library, often related to model behavior or integrations.
- **Feature Requests**: Requests for new capabilities or enhancements in model handling and agent interactions.
- **Regressions**: Occasions where previously functional behavior stops working after updates.
- **Documentation Issues**: Clarifications or errors identified in the documentation.
- Issues generally include well-defined reproduction steps and expected vs actual behavior for better clarity.

# Recurring Fix Patterns
- When encountering `ContextWindowExceededError`, the fix is usually to map it to `ContextWindowOverflowException` in `strands-py/src/strands/models/litellm.py`.
- For issues with API key handling, verify the parameters being passed to the `Agent` initializer, ensuring they match the expected types.
- It's common to add exception handling in model invocations, especially where async calls to external APIs are made to maintain stability.
- If there are integration issues with specific models, updating their client exceptions to map correctly to internal exceptions is a frequent requirement.

# Files / Modules That Change Most Often
| Path                        | Why It Gets Touched                                             |
|-----------------------------|-----------------------------------------------------------------|
| `strands-py/src/strands/models/litellm.py`  | Changes to exception handling and model integration logic.      |
| `strands-py/tests/strands/models/test_litellm.py` | Tests are updated or added to cover new exceptions or behaviors. |

# Pitfalls
- Forgetting to handle exceptions when integrating external models can lead to uncaught errors during agent execution.
- Changing the contract of the model interface without updating dependent components can break functionality.
- Not updating tests in conjunction with code changes, leading to false positives in CI/CD pipelines.

# Test Conventions
Tests are located primarily in the `tests/` directory, following a structure that mirrors the modules they test. Common naming convention includes prefixing test files with `test_` followed by the module name. Tests are executed manually or through CI pipelines, often using `pytest`.

# One Concrete Worked Example
Issue [#974](https://github.com/strands-agents/sdk-python/issues/974): The LiteLLM Model did not throw the `ContextWindowOverflowException` as expected. The fix involved mapping the `ContextWindowExceededError` to the standard `ContextWindowOverflowException` during model invocations. This change ensures better handling of context limits during agent operations. The related PR can be found [here](https://github.com/strands-agents/sdk-python/pull/994).
