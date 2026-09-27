# Repository Identity
The repository **langchain-ai/langgraph** is a low-level orchestration framework for building stateful agents. It is maintained by LangChain and written in Python.

# Typical Issue Shape
- Issues primarily consist of bug reports related to the functionality of the graph and runtime context.
- Many issues are well-specified, including examples and reproduction steps.
- There is no explicit bug report template, but detailed examples accompany issues.

# Recurring Fix Patterns
- When you see an issue related to context not being passed, the fix is usually to modify the handling of the context in `libs/langgraph/langgraph/_internal/_runnable.py`.
- If the error states `AttributeError: NoneType object has no attribute username`, ensure the context is properly propagated in subgraph invocations.
- Review the test cases in `libs/langgraph/tests/`, which often influence what fixes need to be made based on failing tests.

# Files / Modules That Change Most Often
| Path                                           | Reason for Changes                                |
|------------------------------------------------|--------------------------------------------------|
| `libs/langgraph/langgraph/_internal/_runnable.py` | Handles graph invocations including context      |
| `libs/langgraph/tests/`                       | Contains the test cases that define expected functionality |

# Pitfalls
- Forgetting to set the appropriate context schema when invoking the graph and subgraphs.
- Not updating the function handling when adding new nodes to a subgraph.
- Assuming that all contexts are passed automatically without explicit handling.

# Test Conventions
Tests are located primarily in the `libs/langgraph/tests/` directory. They are invoked using standard Python test runners, and often named with a `test_` prefix. 

# Concrete Worked Example
Issue **#5700**: [Runtime context is not being passed to the subgraph](https://github.com/langchain-ai/langgraph/issues/5700). The fix involved ensuring that the context passed to the main graph is also available in the subgraph during invitations. The issue was resolved by modifying the context handling logic in the invocation methods.
