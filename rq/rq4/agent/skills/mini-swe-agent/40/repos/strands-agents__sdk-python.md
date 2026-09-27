# Repo Identity
This repository comprises a model-driven approach to building AI agents in just a few lines of code. It is implemented in Python, and the primary components are organized under the `strands` package. The repository is maintained by the Strands team.

# Typical Issue Shape
- Predominantly bug reports and requests for feature enhancements.
- Issues are generally well-specified, often including steps to reproduce, expected behavior, and actual behavior.
- Each issue usually contains relevant labels for easy tracking, such as `bug` and `ready for contribution`.

# Recurring Fix Patterns
- When encountering `ContextWindowExceededError`, the fix is usually to map it to `ContextWindowOverflowException` in the model, particularly in `strands-py/src/strands/models/litellm.py`.
- If a test fails due to LLM client exceptions, it often means the exception mapping needs to be updated in `strands-py/src/strands/models/litellm.py`.
- Watching for failure in adopting structured response schemas might require additional checks in the structured output methods.

# Files / Modules That Change Most Often
| Path                                      | Reason for Changes                                      |
|-------------------------------------------|--------------------------------------------------------|
| `strands-py/src/strands/models/litellm.py`          | Fixes related to LLM model exceptions and their mapping. |
| `strands-py/tests/strands/models/test_litellm.py`   | Updates to unit tests reflecting changes in model behavior. |

# Pitfalls
- Forgetting to update exception mappings can lead to unhandled exceptions in the agent.
- Not running tests after modifications can leave bugs unaddressed, especially in edge cases.
- Changes that appear to fix behavior may actually introduce new issues if not properly tested.

# Test Conventions
Tests are located in the `tests/` directory, named conventionally as `test_<functionality>.py`. They are invoked using `pytest` and follow a structure where each test case asserts proper functionality through expected exception handling and outcomes.

# One Concrete Worked Example
**Issue #974: [BUG] LiteLLM Model Does Not Throw ContextWindowOverflowException**  
Created on: 2025-10-03  
Closed on: 2025-10-07  
This issue involved the `LiteLLMModel` not throwing the appropriate `ContextWindowOverflowException` when exceeding context limits. The fix involved mapping `ContextWindowExceededError` to `ContextWindowOverflowException` within `strands-py/src/strands/models/litellm.py`. For further details, visit the issue [here](https://github.com/strands-agents/sdk-python/issues/974) and the related PR [here](https://github.com/strands-agents/sdk-python/pull/994).
