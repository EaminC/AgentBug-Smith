# Aider-AI/aider Skill Notes

## Repo identity
`Aider-AI/aider` is a project focused on AI pair programming in the terminal, specifically designed to assist developers by automating coding tasks. The project is primarily developed in Python and can be used with various language models for enhanced coding suggestions. The repository is managed by Aider, which is maintained by an active community of developers.

## Typical issue shape
- **Bug Reports**: Most issues are related to bugs in the AI functionality, such as failures in file creation (`#1222`).
- **Enhancements**: Requests to add support for new features or refine existing functionalities, like support for new model fields (`#1583`).
- **Intermittent Errors**: Some issues report inconsistent behaviors, requiring investigation across code contexts (`#1675`).
- **Feature Requests**: Many users request support for new models and functionalities, such as for Bedrock/Claude 4.5 (`#4543`).
- **Configuration Problems**: Issues often relate to improper configuration of model settings that cause errors during execution (`#700`).

## Recurring fix patterns
- **When encountering file creation failure (e.g., `SEARCH/REPLACE` blocks not resolving), the fix is usually to adjust the handling in `aider/coders/editblock_coder.py`**. For example, after identifying that a new file was not being created despite being prompted, adding checks for folder structures and ensuring handling is appropriate typically resolves the problem.
  
- **If the `extra_body` field isn't being sent with model requests, ensure the `send_completion` function in `aider/sendchat.py` accommodates it**. For instance, the proper addition of parameters like `extra_body` can help avoid issues related to unsupported fields in API requests.

- **Inconsistent behavior in context handling (e.g., LLM confusion over context) usually requires ensuring the models are correctly identified and passed**. Check how context management is devised in `aider/models.py` and adjust how models are selected based on input structure.

- **Frequent errors with specific model types, such as Vertex AI, require modifications to `aider/models.py` for correct model name parsing**. This is often rectified by normalizing the model naming convention during model instantiation.

- **Issues with commit messages often stem from prompt misconfigurations in `aider/prompts.py`, likely requiring adjustments to the commit generation logic**. 

## Files / modules that change most often
| Path                             | Reason for Change                        |
|----------------------------------|-----------------------------------------|
| `aider/coders/editblock_coder.py`| Handling file creation logic            |
| `aider/sendchat.py`             | Modifications to communication with LLM |
| `aider/models.py`               | Configurations for model settings       |
| `aider/prompts.py`              | Improving commit message generation     |

## Pitfalls
- **Forgetting to adjust the model's parameters** in configuration files can lead to models that cannot correctly interpret the input leading to errors.
- **Assuming patch sizes or diff formats won't affect behavior**, which leads to substantial issues during development.
- **Neglecting to check the integration of new features**, especially in relation to existing tests that may conflict with newly added functionalities.

## Test conventions
Tests for the functionality are located in the `tests/basic` directory, structured to validate fixes and new features. They are typically named `test_<functionality>.py`, and can be run using standard pytest commands.

## One concrete worked example
Issue [`#1222`](https://github.com/Aider-AI/aider/issues/1222) reported that files are not being created as expected. The problem arose due to AI not executing file creations effectively after issuing commands. The linked PR [#1239](https://github.com/Aider-AI/aider/pull/1239) addressed the issue by implementing a proper check and setting ensuring file creation requests are processed correctly.
