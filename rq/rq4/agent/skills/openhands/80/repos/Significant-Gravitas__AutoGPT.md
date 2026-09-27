# Repo Identity
AutoGPT — AI agents that finish the work. The repository can be found at [Significant-Gravitas/AutoGPT](https://github.com/Significant-Gravitas/AutoGPT).
# Typical Issue Shape
Users typically report issues due to compatibility errors, especially when executing shell commands on different operating systems (e.g., Windows versus Linux). Common examples include path-related errors and command syntax issues that arise from OS differences.

# Recurring Fix Patterns
Fixes frequently involve updating the scripts to check for the host OS and adapting commands accordingly. For instance, modifying file path separators and command structures ensures compatibility across environments.
# Files / Modules That Change Most Often
- autogpt/config/ai_config.py
- autogpt_platform/backend/backend/blocks/
- autogpt_platform/backend/load-tests/tests/

# Pitfalls
Developers often forget to test commands for different environments, leading to runtime errors upon execution. There is also a tendency to hard-code paths that may not exist on all systems.

# Test Conventions
Tests should cover various environments to ensure that commands run without issues. This includes verifying the output and side effects when commands are executed in different OS contexts.
# One Concrete Worked Example
### Issue Title
"Inform AI of host OS for execute_shell"

### Issue Description
This issue arose when the AutoGPT application failed to correctly identify the host OS and attempted to execute Linux-specific commands on a Windows machine, as documented in the issue report [here](https://github.com/Significant-Gravitas/AutoGPT/issues/2390).
