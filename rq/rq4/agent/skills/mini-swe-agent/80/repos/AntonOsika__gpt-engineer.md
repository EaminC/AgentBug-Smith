# Repo Identity
The repository `gpt-engineer` facilitates the usage of AI models for various applications, specifically incorporating the new capabilities of the `gpt-4-turbo` model. The codebase is primarily written in Python, using frameworks such as Typer and Langchain to manage command-line interfaces and model interactions. The project is maintained by Anton Osika and contributors.

# Typical Issue Shape
- Issues primarily involve bug reports related to model functionality and features, with users detailing expected versus current behavior.
- Features may request enhancements or new capabilities interpreted from user feedback.
- Bug templates ensure users provide reproduction steps and relevant system details, allowing for well-specified issue submissions.

# Recurring Fix Patterns
- When you see `model_name` not recognizing `gpt-4-turbo`, the fix is usually to update the condition for setting `self.vision` in `gpt_engineer/core/ai.py`.
- When a model fails to process images, a common fix involves checking and updating the `langchain` dependency to a suitable version.
- Bugs related to command-line flags usually have documentation in `gpt_engineer/applications/cli/main.py`.

# Files / Modules that Change Most Often
| Path                           | Reason for Changes                               |
|--------------------------------|-------------------------------------------------|
| `gpt_engineer/core/ai.py`     | Modifications to model initialization behavior    |
| `gpt_engineer/applications/cli/main.py` | Updates to command handling and parameters     |
| `tests/test_vision.py`        | New tests for features and bug fixes                |

# Pitfalls
- Forgetting to update dependencies can lead to failure in recognizing new models.
- Incorrect model name checks may lead to silent failures where features are not enabled.
- Assuming flags without checking their implementation path can overlook critical functionality.

# Test Conventions
Tests reside in the `tests/` directory, and are typically invoked via `pytest`. Test files usually start with `test_` followed by the relevant issue number or functionality being tested.

# One Concrete Worked Example
**Issue 1112:** [Missing support for the vision capabilities in the new model gpt-4-turbo](https://github.com/AntonOsika/gpt-engineer/issues/1112) outlines the failure of the model to process images due to a condition not accounting for the `gpt-4-turbo` model. The fix included updates to both `ai.py` and requires a dependency on a newer version of `langchain`. Related PR: [#1121](https://github.com/AntonOsika/gpt-engineer/pull/1121).
