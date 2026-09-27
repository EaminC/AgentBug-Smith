# Repo Identity

The repository `AntonOsika/gpt-engineer` aims to aid in the development of an AI agent utilizing the AI agent SDK. This project is maintained by Anton Osika, featuring a diverse codebase that includes Docker components, as well as libraries for managing AI functionalities.

# Typical Issue Shape
- Bug reports are common, often detailing issues with AI response accuracy or unexpected behaviors.
- Feature requests appear fairly regularly, with users suggesting enhancements to the AI capabilities.
- Sometimes, regression issues arise when new features inadvertently affect existing functionality.
- Issues typically contain specific reproduction steps, although some may require clearer description or context.

# Recurring Fix Patterns
- When you see a regression in AI performance, the fix is usually to review changes in `gpt_engineer/` that affect the response handling.
- If an issue pertains to Docker configurations, updating the `docker/` settings or services will often resolve it.
- For errors related to testing failures, the fix is often in the `tests/` module, specifically ensuring proper test setups in test scripts.
- Issues reported regarding external APIs typically require examining integration points within `scripts/` and `gpt_engineer/`.
- When encountering issues specifically tied to modules, the fixes often involve updating class methods interfacing within `gpt_engineer/`. 

# Files / Modules That Change Most Often
| Path                     | Why It Gets Touched              |
|--------------------------|----------------------------------|
| `docker/`                | Changes in environment settings.  |
| `gpt_engineer/`          | Core functionality enhancements. 
| `scripts/`               | Integration and utility updates. 
| `tests/`                 | Adding new tests based on reported issues. 
| `projects/`              | New project implementations or updates.  

# Pitfalls
- Forgetting to update the Docker configurations after environmental changes can lead to deployment issues.
- Mismatching async and sync functions can result in runtime errors and should be carefully handled.
- Unaddressed edge cases in API handlers might create unexpected behavior in the agent's responses.
- Not providing sufficient reproduction steps when reporting issues can make resolution more challenging.
- Failing to document changes in API schemas can break frontend integration points.

# Test Conventions
Tests are located in the `tests/` directory, where files are generally named following the convention `test_<feature>.py`. Tests are executed using the command `pytest`, ensuring coverage of core functionalities and regression tests.

# One Concrete Worked Example
**Issue #42**: "Adjust AI response handling to improve accuracy in specific scenarios" - This issue was addressed through a patch that refined the handling of contextual prompts, linked to the pull request [PR #22](https://github.com/AntonOsika/gpt-engineer/pull/22).