# Notes for the Strands Agents SDK Python

## Repo identity
The \'strands-agents/sdk-python\' repository implements a model-driven approach to building AI agents using Python. The codebase is maintained within the Strands organization and contains various modules organized under the \'src\' directory.

## Typical issue shape
- Issues often come in the form of bug reports regarding the behavior of AI agents.
- Feature requests are also common, particularly around enhancing agent capabilities.
- Issues may include detailed reproduction steps, expected vs actual behavior, and potential solutions.
- A typical issue will include checks that the reporter has completed, such as verifying the latest version of Strands and confirming no duplicates.

## Recurring fix patterns
- When you see \'ContextWindowExceededError\', the fix is usually to catch this error and raise the appropriate \'ContextWindowOverflowException\' in \'src/strands/models/litellm.py\'.
- If you encounter input handling errors, check if the input exceeds the model's context window; add validation or exception handling in the corresponding model class.
- Debug issues related to model responses by ensuring \'supports_response_schema\' is properly set in configurations.
- For agent-function calls that raise unexpected exceptions, implement a try-except block to manage errors gracefully and ensure specialized exceptions are raised.

## Files / modules that change most often
| Path                           | Reason for changes                                   |
|--------------------------------|-----------------------------------------------------|
| \'src/strands/models/litellm.py\'| Handles logic for LiteLLM model interactions        |
| \'tests/strands/models/test_litellm.py\' | Testing LiteLLM exceptions and behaviors      |
| \'src/strands/agent/agent.py\'  | Manages agent invocation and stream execution       |

## Pitfalls
- Forgetting to map model-specific errors to generic exceptions may lead to unhandled cases.
- Assuming thread-safety in async calls without proper synchronization can cause state inconsistencies.
- Changing model configurations without updating corresponding tests can lead to unexpected failures in continuous integration pipelines.

## Test conventions
Tests are located primarily under the \'tests\' directory, mirroring the structure of the source files. Tests are conventionally named to correspond with the featured functionality or identified issues, often prefixed with \'test_\'. The tests can be run using the \'pytest\' framework from the root of the repository.

## One concrete worked example
**Issue #974: [BUG] LiteLLM Model Does Not Throw ContextWindowOverflowException**  
This issue was caused when the \'LiteLLMModel\' did not properly handle overflow exceptions. The fix involved modifying \'src/strands/models/litellm.py\' to catch \'ContextWindowExceededError\' and raise \'ContextWindowOverflowException\'. The corresponding PR can be found [here](https://github.com/strands-agents/sdk-python/pull/994).
