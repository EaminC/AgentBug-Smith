# Repo Identity
This repository, **openinterpreter/open-interpreter**, provides tools for repo-wide maintenance under the name 'codex-monorepo'. It includes various tools and methods for managing and maintaining language models like GPT-4. The repository is maintained by the community and is available in multiple languages.

## Typical Issue Shape
- Bug reports primarily concerning the functionality of the AI agent SDK.
- Feature requests for improved error handling and management.
- User feedback about costs associated with AI services.
- Issues are moderately specified, often providing reproduction steps or example commands.

## Recurring Fix Patterns
- When encountering an issue with cost warnings, adding a '%tokens' command typically resolves it in .
- If conversation restoration fails due to a KeyError, ensure that the correct keys ('message', 'content', etc.) are being used in .
- For testing functions, verify function existence using mock instances, as seen in .

## Files / Modules That Change Most Often
| Path                                        | Why It Gets Touched                                      |
|---------------------------------------------|---------------------------------------------------------|
|  | To add or modify magic commands such as '%tokens'.      |
|  | To address issues with restoring conversations.         |
|        | To improve token counting methods and cost estimation.  |

## Pitfalls
- Forgetting to handle all possible keys in messages, which can lead to errors.
- Not updating the documentation alongside code changes can mislead users.
- Assuming that all users have the same environment setup leading to discrepancies in behavior.

## Test Conventions
Tests are located primarily in the  directory and are named . They can be run using  or directly by invoking the test runner. Each test ensures that the respective feature functions correctly under various scenarios.

## Concrete Worked Example
**Issue 596: High LLM Costs** - This issue concerned the lack of notifications for token consumption, leading users to unknowingly exceed budgets. The problem was resolved by implementing a '%tokens' command, which was merged in [PR 607](https://github.com/openinterpreter/open-interpreter/pull/607).
