# Repo Identity
The `strands-agents/sdk-python` repository is focused on providing a set of Python agents and models, particularly designed for various tasks in robotics and AI interactions. It is maintained by the Strands project team.

# Typical Issue Shape
- Bug reports, especially concerning exception handling and model interactions.
- Feature requests for improvements in model capabilities.
- Issues typically include well-defined reproduction steps and comparisons of expected vs. actual behavior.

# Recurring Fix Patterns
- When encountering `ContextWindowExceededError`, the fix usually involves mapping it to a standard `ContextWindowOverflowException` within the `src/strands/models/litellm.py` module.
- Ensure that exceptions raised in helper libraries are properly caught and rethrown as domain-specific exceptions.

# Files / Modules that Change Most Often
| Path                          | Reason for Changes                        |
|-------------------------------|------------------------------------------|
| `src/strands/models/litellm.py` | Exception handling improvements         |
| `tests/strands/models/test_litellm.py` | Tests related to model exception behaviors |

# Pitfalls
- Skipping the addition of new tests after making changes to exception handling.
- Ignoring context length limits in model invocations.
- Forgetting to update any related models or interfaces that expect certain exceptions to be raised.

# Test Conventions
Tests are primarily located in the `tests` directory. They are invoked with `pytest`, and there are naming conventions such as `test_<module>_<description>.py`.

# One Concrete Worked Example
- **Issue ID**: 974
- **Summary**: The issue concerned the `LiteLLMModel`'s failure to correctly raise a `ContextWindowOverflowException` when the input exceeds the context window limit. This was detailed in the [GitHub issue](https://github.com/strands-agents/sdk-python/issues/974) and resolved in pull request [#994](https://github.com/strands-agents/sdk-python/pull/994).
