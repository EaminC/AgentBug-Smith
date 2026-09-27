# Repo identity
Significant-Gravitas/AutoGPT

# Typical issue shape
Issues commonly arise from the inability of AutoGPT to correctly identify the host operating system, leading to incompatible command executions when switching between Linux and Windows environments.

# Recurring fix patterns
- Ensuring that command executions use platform-agnostic syntax or checking the host OS before executing shell commands.

# Files / modules that change most often
- Files in the `src/` directory, especially those handling command executions and configurations related to dependencies and environment.
# Pitfalls
- Not checking if the system is Windows or Linux before executing OS-specific commands.
- Assuming all paths and command syntax are the same across different operating systems.

# Test conventions
- Use unit tests to cover changes to critical functionality, and ensure integration tests verify overall system behavior across different operating systems.
# One concrete worked example
The issue titled **"Inform AI of host OS for execute_shell"** demonstrates the problem where AutoGPT attempts to execute Linux commands on a Windows machine, resulting in command failures.
