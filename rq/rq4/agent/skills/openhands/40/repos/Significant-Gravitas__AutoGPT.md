Repo identity
This repository is called AutoGPT. It allows users to build and run AI agents that complete tasks based on user input.
Typical issue shape
Issues commonly involve the AI agents not executing commands due to host OS discrepancies or incorrect file paths in commands.
Recurring fix patterns
Adjusting the AI commands to check for the host OS before execution and ensuring correct file paths are specified for the environment.
Files / modules that change most often
The files related to command execution and AI configuration, particularly in 'autogpt/config' and any command-executing modules, are modified regularly.
Pitfalls
Not handling OS-specific commands can lead to errors, particularly when switching between Unix-like and Windows systems.
Test conventions
Tests are typically located under the 'test' directory and focus on verifying the correct functionality of AI agent commands and performance under different conditions.
One concrete worked example
### Issue: Inform AI of host OS for execute_shell\nURL: https://github.com/Significant-Gravitas/AutoGPT/issues/2390
