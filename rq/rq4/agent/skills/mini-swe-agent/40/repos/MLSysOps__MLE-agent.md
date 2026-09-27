# Repo identity
The `MLE-Agent` is an AI agent SDK aimed at automating MLE processes and improving the workflow in AI engineering and research. This repository is maintained by the organization `MLSysOps`.

# Typical issue shape
- Issues generally appear as bug reports and feature requests.
- Many questions are raised regarding functionalities and usage of the agent.
- User issues tend to be well-specified, often detailing reproduction steps.
- There seems to be an informal template for feature requests as users often detail descriptions of their requirements.

# Recurring fix patterns
- When you see requests to **restart previous sessions**, the fix is usually to implement or address caching mechanisms in `mle/utils/cache.py`.
- Questions about **data persistence** typically involve modifications to the `WorkflowCache` class in `mle/utils/cache.py`.
- For issues related to **agent memory management**, review the `WorkflowCacheOperator` methods in `mle/utils/cache.py`.

# Files / modules that change most often
| Path                          | Reason it gets touched                                   |
|-------------------------------|--------------------------------------------------------|
| `mle/utils/cache.py`          | Implementing caching logic to enable session resumption. |
| `mle/utils/system.py`         | Handling configuration and system utilities.             |

# Pitfalls
- Ensure to **update config files** when adding caching logic.
- Be cautious of **data serialization issues** when pickling objects to cache.
- Forgetting to **initialize cache states** can lead to unresolved references when resuming sessions.

# Test conventions
The tests for this repository are primarily located within the `tests` directory and generally follow the naming convention of `test_<feature>.py`. Testing is invoked through standard testing frameworks like `pytest` or any CI/CD setups outlined in `.github/workflows/test.yml`.

# One concrete worked example
Issue [#121: Restarting previous session](https://github.com/MLSysOps/MLE-agent/issues/121) asked for a way to resume a previous session after a glitch. This issue was addressed in PR [#123](https://github.com/MLSysOps/MLE-agent/pull/123) which introduced the ability to cache and restore previous session states via `WorkflowCacheOperator` in `mle/utils/cache.py`.
