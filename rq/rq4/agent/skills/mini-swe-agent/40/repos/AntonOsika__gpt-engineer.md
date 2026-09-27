# Repo identity
The repository `AntonOsika/gpt-engineer` focuses on developing AI agent SDK features, particularly enhancing capabilities for various models including `gpt-4-turbo`. 

# Typical issue shape
- Issues primarily consist of bug reports and feature requests.
- Expected behavior and current behavior are usually well-specified.
- Users suggest fixes including version updates and changes to specific code lines.

# Recurring fix patterns
- When you see `vision capabilities not working`, the fix is usually to include `gpt-4-turbo` in the check for the vision attribute in `gpt_engineer/core/ai.py` as follows:
  ```python
  self.vision = "vision" in model_name or model_name in ["gpt-4-turbo", "gpt-4-turbo-2024-04-09"]
  ```
- Validate changes ensuring `vision=True` for models like `gpt-4-turbo` in tests.

# Files / modules that change most often
| Path                                      | Why it gets touched                                            |
|-------------------------------------------|---------------------------------------------------------------|
| `gpt_engineer/core/ai.py`            | Changes to the `AI` class's vision property.              |
| `gpt_engineer/applications/cli/main.py` | Updates to command-line argument handling for models.        |

# Pitfalls
- Forgetting to update model checks for new models like `gpt-4-turbo` can lead to failures.
- Ensure dependencies are explicitly stated in `pyproject.toml` to avoid version issues.
- All associated tests (like `fail2pass_test.py`) must confirm the fix correctly.

# Test conventions
Tests generally reside in the `tests/` directory and are named directly corresponding to issues (`test_<issue_number>.py`).

# One concrete worked example
Issue [#1112](https://github.com/AntonOsika/gpt-engineer/issues/1112) titled "Missing support for the vision capabilities in the new model gpt-4-turbo" was resolved by PR [#1121](https://github.com/AntonOsika/gpt-engineer/pull/1121), modifying the `AI` class's vision attribute logic to handle `gpt-4-turbo` correctly.
