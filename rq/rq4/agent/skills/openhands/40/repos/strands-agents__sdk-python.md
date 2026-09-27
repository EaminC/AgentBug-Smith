# Repo Identity
Strands Agents is a model-driven approach to building AI agents in just a few lines of code. This repository includes a monorepo containing shared Python tooling for the Strands monorepo. Maintained by Strands, it features both Python and TypeScript SDKs.

---

# Typical Issue Shape
- **Bug Reports**: Issues related to unexpected behavior in the agents or tools.
- **Feature Requests**: Suggestions for adding new features to the SDK, often well-defined.
- **Regressions**: Problems where previously working functionality stops working after updates.
- **Documentation Improvements**: Requests for clearer or expanded documentation for various components.
- **Code Maintenance**: Issues related to outdated dependencies or improvements in code quality.

---

# Recurring Fix Patterns
- When you see **non-responsive agent**, the fix is usually to check the agent's lifecycle hooks in `strands-py/src/strands/agent/agent.py`.
- When you see **failing tests in `test-infra`**, the fix often involves updating the fixtures used in `test-infra/test_agents.py` to match the agent implementation changes.
- When the issue is about **missing dependencies**, most likely the fix involves adjusting the dependencies in `pyproject.toml`.
- When encountering **type errors**, the resolution typically requires updating the type annotations in functions defined in `src/strands-py/*` to align with usage.
- When **async/sync mismatches** occur, the fix is typically to ensure that all calls to async functions await correctly in `strands-py/src/strands/agent/agent.py`.

---

# Files / Modules That Change Most Often
| Path                       | Why it gets touched                                      |
|----------------------------|--------------------------------------------------------|
| `strands-py/src/strands/agent/agent.py` | Contains core agent logic and lifecycle management.         |
| `strands-py/src/strands/types/tools.py` | New tools are added and existing ones maintained.          |
| `src/strands-py/`         | Updates made for SDK functionalities and bug fixes.      |
| `src/strands-ts/`         | Frequent changes related to TypeScript SDK features.     |
| `test-infra/`             | Regularly updated test cases for validating agent behaviors.

---

# Pitfalls
- Forgetting to properly handle exceptions in the agent lifecycle can lead to silent failures.
- Assuming document structures in `README.md` without confirming alignment with patch updates.
- Not updating both Python and TypeScript SDKs when making agent logic changes.
- Overlooking changes in project dependencies when addressing issues in `pyproject.toml`, which could lead to mismatched environments.

---

# Test Conventions
Tests are located primarily in the `test-infra/` directory and are run using `pytest`. Each test file generally follows the naming convention `test_<name>.py`. Tests are expected to cover all major features and any new issues addressed by providing corresponding tests; for instance, if a new feature is added, a test that describes its behavior must be found in `test-infra/`.

---

# Concrete Worked Example
For issue **#123**: "Agent fails to initialize properly", a fix was implemented in PR **#456**. The patch involved revising the initialization function in `strands-py/src/strands/agent/agent.py` to ensure proper context settings on agent startup. You can view issue details [here](https://github.com/strands-agents/harness-sdk/issues/123) and the related PR [here](https://github.com/strands-agents/harness-sdk/pulls/456).