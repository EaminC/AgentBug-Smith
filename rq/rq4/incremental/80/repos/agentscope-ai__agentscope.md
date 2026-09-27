# Repo Identity

The `agentscope-ai/agentscope` repository hosts **AgentScope: A Flexible yet Robust Multi-Agent Platform**, maintained by the `agentscope-ai` organization.

# Typical Issue Shape
- The repository mainly receives bug reports and feature requests.
- Issues are well-specified with structured reproduction steps often provided.
- Most issues are labeled appropriately (e.g., Bug).

# Recurring Fix Patterns
- When you see `PATCH_MISSING.txt`, the fix is usually clarified within the issue body.
- If `_json_loads_with_repair` causes crashes, check for complex JSON handling.
- When concurrent writes to `AsyncSQLAlchemyMemory` cause `Duplicate Entry`, introduce locking mechanisms.

# Files / Modules that Change Most Often
| Path                                             | Reason for Change                                          |
| ------------------------------------------------ | --------------------------------------------------------- |
| `src/agentscope/hooks/_studio_hooks.py`         | Changes to improve stability and error handling in hooks. |
| `src/agentscope/model/_dashscope_model.py`      | Updates for handling different model types and memory.    |
| `src/agentscope/_utils/_common.py`              | Fixes for JSON handling across various inputs.            |

# Pitfalls
- Forgetting to register hooks after recovering plans can lead to missed events.
- Directly calling synchronous functions in an async context can block execution.
- Failing to ensure proper file extensions for local files can raise errors in processing.

# Test Conventions
Tests are located primarily in the `tests/` directory and are usually named with a `test_` prefix followed by the feature or functionality being tested.

# Concrete Worked Example
- **Issue #102: [Bug]: Missing `__init__.py` for `agentscope.web.studio`.**
    - This issue was resolved by introducing the required `__init__.py` file to make the directory a package.
    - Linked PR: [PR #106](https://github.com/agentscope-ai/agentscope/pull/106).

