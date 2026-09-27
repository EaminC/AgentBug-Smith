# Repo Identity
The repository **Aider-AI/aider** implements AI pair programming in the terminal with a focus on various integrations and model configurations. The primary language used is Python.

# Typical Issue Shape
- Bug reports related to the creation of files and handling of model prompts.
- Enhancement requests for additional features such as support for new fields in model metadata.
- Issues with model context perceptions causing operational confusion.
- Problems with commit messages formatting.
- Documentation requests regarding support for new models or configurations.

# Recurring Fix Patterns
- When you see **issues with file creation**, the fix is usually related to the logic in `aider/coders/editblock_coder.py`.
- When you see **support requests for new model features**, looking into `aider/models.py` allows you to extend functionality, especially for `extra_body` fields.
- When you see **context confusion related to models**, reviewing `aider/models.py` and strengthening its settings often resolves the issues.

# Files / Modules that Change Most Often
| Path                             | Reason                                 |
|----------------------------------|----------------------------------------|
| `aider/models.py`               | Model configurations and format fixes  |
| `aider/coders/editblock_coder.py` | Fixing file creation logic              |
| `aider/sendchat.py`              | Adjustments for handling different API models |
| `aider/resources/model-settings.yml` | Configuration for models integrations   |

# Pitfalls
- Forgetting to properly handle the `SEARCH/REPLACE` logic when editing files can lead to empty outputs or mismatches.
- Not validating new model features against existing configurations can cause runtime errors.
- Assuming that all models accept an `extra_body` without implementing necessary changes.

# Test Conventions
Tests reside primarily in the `tests/basic` directory, with naming conventions that follow the format `test_<functionality>.py`. They can be run using pytest, and typically aim to ensure compliance with expected behavior based on previous issues and patches.

# One Concrete Worked Example
**Issue #1222: Files are not being created**. This issue arose after version 0.53, where a regression caused files not to be generated when requested. A fix was implemented by modifying the logic around file creation in the `aider/coders/editblock_coder.py`. The issue can be accessed [here](https://github.com/Aider-AI/aider/issues/1222), and the corresponding PR can be found [here](https://github.com/Aider-AI/aider/pull/1239).
