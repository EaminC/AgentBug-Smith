# Repo Identity
The repository 'openinterpreter/open-interpreter' contains tools for repository-wide maintenance, primarily focusing on an AI agent SDK. It currently supports various versions and features that enhance user interaction with interpreters.

# Typical Issue Shape
- Issues commonly include bug reports, feature requests, and regressions.
- Issues are generally well-specified with reproduction steps, expected outcomes, and actual behaviors.
- There may be references to specific features or improvements in the issue body.

# Recurring Fix Patterns
- When you see **high costs from the LLM**, the fix often involves **adding warning messages concerning token consumption**, typically in 'interpreter/terminal_interface/magic_commands.py'.
- When the issue is about **conversation restoration**, the solution frequently entails **modifying message retrieval logic** in 'interpreter/terminal_interface/render_past_conversation.py'.

# Files / Modules That Change Most Often
| Path                                         | Reason it gets touched                                   |
|----------------------------------------------|---------------------------------------------------------|
| 'interpreter/terminal_interface/magic_commands.py'  | For adding or modifying command functionalities           |
| 'interpreter/terminal_interface/conversation_navigator.py' | Changes related to user interface and interaction          |
| 'interpreter/terminal_interface/render_past_conversation.py' | Bug fixes and updates related to message displaying logic |

# Pitfalls
- Forgetting to handle **token accounting** can lead to high costs in LLM.
- Assuming the old format still works post-update can cause errors (seen in conversation restoration).
- Overlooking the necessity of updating tests that validate new feature integrations.

# Test Conventions
Tests are typically located alongside their respective modules with naming conventions like 'test_<module>.py'. They ensure that features function as expected and are invoked using standard Python testing frameworks.

# One Concrete Worked Example
For issue [#596](https://github.com/openinterpreter/open-interpreter/issues/596), the user reported high LLM costs due to missing warnings about token consumption. The solution was merged in PR [#607](https://github.com/openinterpreter/open-interpreter/pull/607), which added a command '%tokens' to inform users about token usage.
