# Repo Identity
The repository `langgraph` is a low-level orchestration framework for building stateful agents, maintained by the `langchain-ai` organization.

# Typical Issue Shape
- Bug reports related to context handling and type requirements.
- Feature requests often focus on enhancing type annotations and making runtime behavior more robust.
- Commonly well-specified issues with example code provided.

# Recurring Fix Patterns
- When you see an `AttributeError` related to context in subgraphs, the fix is usually modifying how contexts are passed in the `libs/langgraph/langgraph/_internal/_runnable.py`.
- If `AgentState` requires updates for type annotations, changes in `libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py` are typical fixes.
- Adding missing variables in TypedDicts like `is_last_step` indicates changes to the respective classes in `chat_agent_executor.py`.

# Files / Modules That Change Most Often
| Path                                            | Reason for Change                         |
|-------------------------------------------------|------------------------------------------|
| `libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py` | Updates to state handling and TypedDicts |
| `libs/langgraph/langgraph/_internal/_runnable.py`        | Changes to runtime configuration handling |
| `libs/langgraph/graph/state.py`                | Modifications for caching behavior        |

# Pitfalls
- Forgetting to update subgraph context management often leads to runtime failures.
- Misconfiguring types when passing dictionaries instead of expected TypedDict can lead to warnings or errors.
- Assuming that changes propagate without explicit definitions in subclasses of contexts.

# Test Conventions
Tests can be found under `libs/langgraph/tests`, generally named following the structure `test_<feature_or_issue_number>.py`. They can be executed using conventional pytest commands.

# One Concrete Worked Example
- **Issue 5700**: [Runtime context is not being passed to the subgraph](https://github.com/langchain-ai/langgraph/issues/5700). The fix involved modifying the `coerce_to_runnable` function in `libs/langgraph/_internal/_runnable.py` to manage PregelProtocol instances explicitly.
