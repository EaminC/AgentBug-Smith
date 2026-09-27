# Repo identity

The repository **AntonOsika/gpt-engineer** is an AI agent SDK designed for generating and improving code through various intelligent prompts. It operates primarily in Python and is intended for use with advanced models such as GPT-4 Turbo. The project is actively maintained by its author, Anton Osika.

---

# Typical issue shape

- **Bug reports** are common, often detailing unexpected behavior with existing functionality.
- Issues may include **feature enhancements**, especially regarding AI capabilities and model support.
- There are **regression reports**, where fixes from earlier updates introduce new bugs.
- The reported issues often contain **specific reproduction steps and expected behaviors**, allowing for clear identification of the problem.

---

# Recurring fix patterns

- **When you see** a lack of support for a model feature (e.g., vision capabilities for GPT-4 Turbo), **the fix is usually** to update class attributes and dependency versions in `gpt_engineer/core/ai.py`. For example, change from:
  ```python
  self.vision = "vision" in model_name
  ```
  to:
  ```python
  self.vision = "vision" in model_name or model_name in ["gpt-4-turbo", "gpt-4-turbo-2024-04-09"]
  ```
- **When you encounter** serialization errors related to classes (e.g., `Prompt`), **the fix is generally** to modify the class to return JSON-compatible strings in `gpt_engineer/applications/cli/learning.py`.
- **When there's a model name conflict**, **the resolution typically involves** updating model handling in `gpt_engineer/core/ai.py` to ensure that deployment names don't overlap with model names.

---

# Files / modules that change most often

| Path                                           | Why it gets touched                               |
|------------------------------------------------|--------------------------------------------------|
| `gpt_engineer/core/ai.py`                      | Frequent updates for model features and fixes.   |
| `gpt_engineer/applications/cli/learning.py`   | Adjustments for learning upload functionalities.  |
| `gpt_engineer/applications/cli/main.py`       | Changes for command-line interface updates.       |
| `gpt_engineer/preprompts/file_format_diff`    | Updates related to prompt formats and handling.  |

---

# Pitfalls

- Forgetting to account for new model names in legacy code can lead to unhandled cases.
- Failing to update corresponding tests after modifying class behavior can result in undetected bugs.
- Overlooking async/sync model discrepancies may introduce runtime errors or unexpected behavior.

---

# Test conventions

Tests reside primarily in the `tests/` directory. They are systematically named with the prefix `test_`, followed by a descriptive title of the functionality being tested (e.g., `test_vision_flag_for_gpt4_turbo`). Tests are run using standard Python testing frameworks.

---

# One concrete worked example

**Issue #1112: Missing support for the vision capabilities in the new model gpt-4-turbo**  
This issue highlighted that images were not being processed when using the `--image_directory` flag with the gpt-4-turbo model. The fix involved updates to dependencies and modifying the AI class to correctly recognize vision capabilities for the model. The related PR can be viewed [here](https://github.com/AntonOsika/gpt-engineer/pull/1121).

---
