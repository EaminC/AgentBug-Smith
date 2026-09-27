# MLE-Agent Issue Fixing Notes

## Repo identity
MLE-Agent is an AI agent designed to automate machine learning engineering processes, aiding users with various tasks in ML projects. Developed in Python, it integrates features for project management and user interaction, maintained by the MLSysOps team. It organizes its codebase under specific folders including `assets/`, `exp/`, `mle/`, `tests/`, and `web/`.

## Typical issue shape
- Issues primarily consist of bug reports and feature requests.
- Many issues are well-specified, often including steps to reproduce the bug or clarify requirements.
- Some issues involve questions about the functionality or usage of the MLE-Agent.
- Observed indications of user confusion regarding specific functionalities, suggesting a need for better documentation or features.
- A "bug template" exists that outlines the description and reproduction steps.

## Recurring fix patterns
- When you see **memory-related issues** (e.g., not being able to resume sessions), a common fix involves initializing the `LanceDBMemory` properly. Example: enhancing `LanceDBMemory` setup to handle the absence of configuration gracefully.
- When encountering **dataset ambiguity**, check and clarify the dataset name provided by users. The typical fix is to implement a method in the advisor agent to suggest datasets based on user input (e.g., `advise.clarify_dataset`).
- For **code generation failures**, validate that the generation pipeline correctly configures the model type. The fix usually involves ensuring proper model invocation and parameter adjustments.
- When facing **API integration problems**, added checks on API endpoints and environment variables are often necessary. Example: ensure the base URLs are correctly set up within the code.
- If you see **missing configuration fields** (like 'search_engine'), the mitigation may involve default-handling techniques in accessing configurations (e.g., using a `.get()` function).
- When tests fail to pass, verify if all necessary modules and dependencies are pre-installed. Often the issue arises from missing packages or incorrect versions in `requirements.txt`.

## Files / modules that change most often
| Path                           | Reason for Change                                       |
|--------------------------------|--------------------------------------------------------|
| `mle/agents/advisor.py`       | Changes relate to advising agents on dataset selection |
| `mle/utils/memory.py`         | Enhancements and fixes for memory management functions  |
| `mle/cli.py`                  | Updates to CLI commands and managing user interactions  |
| `mle/agents/coder.py`         | Fixes for code generation processes                      |
| `mle/utils/system.py`         | Utility functions related to environment setup          |

## Pitfalls
- Forgetting to properly handle `None` cases while accessing configuration values.
- Assuming all dependencies are installed; often users may skip installations leading to runtime errors.
- Not checking whether models have been initialized correctly can cause unexpected behavior.
- Directly modifying the user’s input without validation can lead to errors. Always sanitize or handle inputs carefully.
- Overlooking the need to debug or adjust for environment-specific differences, especially in deployment scenarios.

## Test conventions
Tests are primarily located in the `tests/` directory and are run using pytest. Naming conventions often follow a pattern of `test_<issue_number>.py`, facilitating easy identification of tests corresponding to specific issues.

## One concrete worked example
### Issue 121: Restarting previous session
This issue addressed the lack of functionality to resume previous sessions of the MLE-Agent. The solution implemented a mechanism for `LanceDBMemory` to fetch and restore prior session states effectively. For further details, refer to the issue here: [Issue #121](https://github.com/MLSysOps/MLE-agent/issues/121) and the corresponding pull request: [PR #123](https://github.com/MLSysOps/MLE-agent/pull/123).
