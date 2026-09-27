# Repo Identity
The `Significant-Gravitas/AutoGPT` repository implements AI agents that finish tasks autonomously. Developed in Python, it supports both GPT-3.5 and GPT-4 through OpenAI's API.

# Typical Issue Shape
- Issues often relate to bugs where the AI does not behave as expected under specific configurations.
- Frequently, issues arise when the environment is not adequately detected, leading to executing incorrect commands based on the operating system.
- The issues provide detailed reproduction steps and expected behavior.
- Bug templates are effectively used to ensure reproducibility.

# Recurring Fix Patterns
- When encountering OS-related issues, the fix usually involves updating the configuration in `classic/forge/forge/models/config.py` to get the correct OS information.
- If a model type discrepancy arises, changes are generally applied in `classic/forge/forge/agent_protocol/agent.py` to respect command line flags like `--gpt3only` or `--gpt4only`.

# Files/Modules That Change Most Often
| Path                                   | Why it gets touched                         |
|----------------------------------------|--------------------------------------------|
| `classic/forge/forge/models/config.py`             | Modifications to handle OS detection       |
| `classic/forge/forge/agent_protocol/agent.py`               | Updates for managing AI interactions       |
| `classic/original_autogpt/autogpt/app/configurator.py`              | Adjusting model configurations              |

# Pitfalls
- Forgetting to correctly configure OS checks can lead to execution errors.
- Misunderstanding flag configurations can result in unexpected model usage.
- Failing to thoroughly test for multiple environments may cause compatibility issues.

# Test Conventions
Tests are located within the `tests` directory structured according to functionality. Generally, tests are prefixed with `test_` followed by the feature tested or issue it addresses. For example, `test_ai_config.py` will focus on the AI configuration tests.

# One Concrete Worked Example
**Issue #2390**: "Inform AI of host OS for execute_shell". This issue was highlighted due to failures in executing appropriate commands based on the host OS. The fix included checking the OS and modifying the AI configuration for accurate command execution.
Link: [Issue 2390](https://github.com/Significant-Gravitas/AutoGPT/issues/2390)
