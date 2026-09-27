# Aider-AI/aider

## Repo Identity
The repository **Aider-AI/aider** is focused on implementing an AI pair programming assistant in a terminal interface. Written primarily in Python, it provides support for various AI models and enhances developer productivity through interactive coding assistance. The project is actively maintained by contributors who focus on integrating AI capabilities with development workflows.

## Typical Issue Shape
- Issues commonly include bug reports, feature requests, and enhancement discussions related to AI model support.
- The issues tend to include detailed descriptions and expected behavior, but may sometimes lack reproduction steps.
- Users typically express frustration or confusion with new features or changes that break existing functionalities.
- Each issue is managed under GitHub's typical structure, including labels and linked pull requests when resolutions are proposed.

## Recurring Fix Patterns
- When you see **files not being created**, the fix usually involves updating methods that handle file creation in the `aider/coders/editblock_coder.py` module.
- For **addition of fields in model settings**, check the `aider/models.py` to ensure the new attributes, such as `extra_body`, are properly integrated with the existing model configurations.
- If Aider has **confusion about context**, the resolution often involves resetting the context or properly managing the added files in the session, particularly in `aider/sendchat.py`.
- When models like **vertex_ai/claude_* models** return errors, the fix is generally in normalizing the model name format in `aider/models.py`.
- Issues with **commit messages ** can often be resolved by refining the prompts in `aider/prompts.py` to ensure outputs are valid and concise.

## Files / Modules That Change Most Often
| Path                         | Reason for Change                                |
|------------------------------|--------------------------------------------------|
| `aider/coders/editblock_coder.py` | Handles file creation and manipulation.           |
| `aider/models.py             | Configuration of AI models and related settings. |
| `aider/sendchat.py           | Manages message and context interaction.         |
| `aider/prompts.py            | Improves how commit messages are generated.      |
| `tests/basic/test_editblock.py | Contains tests related to the functionality of editing blocks.|

## Pitfalls
- Forgetting to update **the model settings** after adding new features can lead to regressions or failures.
- Incorrect handling of **async/sync function calls** within the assistant logic can lead to unpredictable behaviors.
- Failing to adapt **context management**, especially when dealing with file uploads or context resets, can confuse the assistant.
- Forgetting to review **test cases** before and after implementing changes may lead to broken functionality or untested features.

## Test Conventions
Tests reside under the `/tests/` directory, following a naming convention of `test_<module_name>.py` for easy identification. Tests can be run using the pytest framework, focusing on ensuring that functionalities remain intact through changes. 

## Concrete Worked Example
- **Issue #1222: Files are not being created**  
  Users reported problems with file creation after interacting with the system. This issue was closed with a fix in [PR #1239](https://github.com/Aider-AI/aider/pull/1239), which handled the creation logic in `aider/coders/editblock_coder.py` effectively. The implemented changes included enhanced checks for file operations during refactoring.
