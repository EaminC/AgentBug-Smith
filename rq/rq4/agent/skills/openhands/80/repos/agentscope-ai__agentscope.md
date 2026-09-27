# Repo Identity

The `agentscope-ai/agentscope` repository implements AgentScope, a flexible yet robust multi-agent platform. It is primarily developed using Python and contains multiple subdirectories for organizational structure, including `assets/`, `examples/`, `scripts/`, `src/`, and `tests/`. 


# Typical Issue Shape
- Common issues include bug reports, feature requests, and regressions.
- Issues generally include reproduction steps and expected versus actual behavior.
- There might be a template used for bug reports, leading to consistent information.


# Recurring Fix Patterns
- When you see a failure in `src/tests/test_example.py`, the fix is usually updating the expected outcomes in the test.
- If `src/src/agent.py` throws an error about missing parameters, the fix is typically adjusting the invocation of the relevant function to include the necessary parameters.
- Seeing a deprecation warning in `src/utils.py` usually means you need to update the code to conform to current library standards.
- Encountering issues with Docker setup in `env.dockerfile` often leads to correcting environment variable configurations or installing missing dependencies.


# Files / Modules That Change Most Often
| Path                        | Why It Gets Touched                          |
|-----------------------------|----------------------------------------------|
| `src/src/agent.py`        | Main agent implementations, frequently updated to fix bugs or add features.
| `src/tests/test_example.py`| Regularly modified to enhance test coverage for new features or bug fixes.
| `env.dockerfile`          | Changed often due to updates in dependency management or environment setups.
| `src/utils.py`            | Common function utilities may need updates for changing dependencies or API changes.


# Pitfalls
- Forgetting to update the test when changing functionalities can lead to failed tests that don't reflect current behavior.
- Mixing synchronous and asynchronous calls can cause race conditions or unexpected behavior.
- Not considering backward compatibility can break existing implementations when changes are made.
- Changing external API parameters without fully understanding downstream effects can lead to larger issues.


# Test Conventions
Tests are located primarily in the `src/tests/` directory, and they follow naming conventions like `test_<feature>.py`. They are typically invoked using standard pytest commands, providing strong coverage for every issue addressed in the codebase.


# One Concrete Worked Example
Issue #52: Incorrect handling of user input during the agent invocation led to failure in `src/src/agent.py`. The issue was addressed by modifying the input validation logic, implemented in PR #134, which can be viewed for detailed changes. **Link to Issue:** [#52](https://github.com/agentscope-ai/agentscope/issues/52) | **Link to PR:** [#134](https://github.com/agentscope-ai/agentscope/pull/134)  
