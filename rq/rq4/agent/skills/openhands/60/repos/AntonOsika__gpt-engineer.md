# Repo identity

This repository, `AntonOsika/gpt-engineer`, is focused on providing an AI agent SDK for building customizable AI-driven applications. The repository leverages Python as its primary programming language and is maintained by Anton Osika and contributors. The source code is organized under various top-level subdirectories including `docker/`, `gpt_engineer/`, `projects/`, `scripts/`, and `tests/`.

# Typical issue shape
- Issues typically include bug reports, feature requests, and regression bugs.
- The issues are well-specified, often containing clear descriptions and steps to reproduce.
- There is a defined bug template that provides a structured format for submissions, including reproduction steps and expected behavior.

# Recurring fix patterns
- When you see a regression in functionality, the fix is usually found in `gpt_engineer/agent.py` where the state management logic is updated to reflect the new requirements.
- If tests related to Docker operations fail, check `docker/` for any breaking changes in the container configurations.
- For issues with test failure due to misconfigured paths, the solution often lies in `tests/conftest.py` where paths and fixtures may need adjustments.
- When encountering integration points breaking, revisit the API changes documented in `gpt_engineer/api.py` to align with expected inputs.
- When you see failures related to external service calls, ensure to review the error handling procedures in `gpt_engineer/utils.py`, which manage API integrations.

# Files / modules that change most often
| Path                             | Why it gets touched                                            |
|----------------------------------|--------------------------------------------------------------|
| `gpt_engineer/agent.py`          | Core agent logic and state management adjustments.            |
| `tests/`                         | Regular updates for new tests corresponding to added features.|
| `docker/`                        | Configuration updates to ensure compatibility with new features.|
| `gpt_engineer/api.py`           | Changes based on API evolution impacting external integrations.|
| `gpt_engineer/utils.py`         | Utility function updates for new service integrations.        |

# Pitfalls
- Forgetting to update the Docker environment configurations; ensure `docker/` is synced with code changes.
- Overlooking updates to both synchronous and asynchronous functions which can lead to inconsistent behavior.
- Not updating integration service configurations, which often leads to timeouts or misrouting of requests.
- Failing to check the compatibility of new features with existing test cases that may lead to tests passing incorrectly.

# Test conventions
Tests are typically housed within the `tests/` directory. They can be invoked using `pytest` or similar frameworks. Naming is generally structured as `test_<feature_or_issue_number>.py`, helping in easily correlating tests with specific issues or functional areas.

# One concrete worked example
Issue 42: "Docker container fails to build due to missing dependencies" was resolved by updating the `docker/Dockerfile` to include additional Python packages as specified in the issue discussion. For detailed information, refer to [Issue 42](https://github.com/AntonOsika/gpt-engineer/issues/42) and the linked PR.