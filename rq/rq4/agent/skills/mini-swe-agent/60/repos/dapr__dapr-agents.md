# Repo Identity
The repository `dapr/dapr-agents` is maintained by The Dapr Authors and is designed for creating agentic workflows made simple. The code is primarily written in Python, and the structure includes directories such as `dapr_agents/`, `examples/`, `ext/`, `schemas/`, and `tests/`.

# Typical Issue Shape
- Issues tend to include bug reports and feature requests.
- Bug reports are usually well-specified with clear reproduction steps.
- Feature requests often propose enhancements to existing functionality.
- There is a typical structure to issues with a title, description, labels, and linked PRs.
- Issues can span various parts of the agent's functionality, emphasizing agent workflow and tool invocation.

# Recurring Fix Patterns
- **When a workflow needs to handle completion callbacks,** the fix is usually to add a callback parameter in `dapr_agents/llm/base.py` for `OrchestratorBase`. This allows workflows to react programmatically to their completion results. ("add callback method to orchestrator to get final output")
  
- **When encountering concurrency issues,** removing locks in workflow scheduling, `dapr_agents/llm/base.py`, prevents blocking behavior when multiple workflows are initiated. ("remove lock on workflow creation for runner as it blocks scheduling of other workflows")
  
- **When tool invocation fails due to handling errors improperly,** adjust `dapr_agents/tool/mcp/client.py` to ensure proper feedback from the error response, allowing content from the MCP server to be returned correctly. ("return the content if hasattr(result, 'content') && hasattr(content, 'text') to reiterate from the model")
  
# Files / Modules That Change Most Often
| Path                                | Reason for Frequent Changes                               |
|-------------------------------------|---------------------------------------------------------|
| `dapr_agents/llm/base.py` | Introduces callback mechanisms for workflows            |
| `dapr_agents/llm/base.py`    | Changes related to workflow concurrency handling         |
| `dapr_agents/tool/mcp/client.py`           | Modifications for error handling in tool invocation      |
| `tests/workflow/test_workflow_runner.py`       | Tests related to the concurrency and scheduling behavior |
| `tests/tool/test_mcp_client.py`                 | Tests on MCP client behavior and output handling         |

# Pitfalls
- Forgetting to update all references across callbacks when modifying function parameters might lead to runtime errors.
- Not handling asynchronous behavior could lead to missed updates or responses in workflows.
- Fixing one part of error handling might create silent failures if not comprehensive across all paths for invoking tools.
- Patching a tool's logic without verifying related tests may lead to regressions.

# Test Conventions
Tests are located under the `tests/` directory, with naming conventions typically starting with `test_`. They are executed using the `pytest` framework, which is compatible with the Python modules used in the repository. There are specialized tests for workflows and agents to ensure comprehensive coverage.

# One Concrete Worked Example
For issue [#209](https://github.com/dapr/dapr-agents/issues/209), titled "workflow completion callback capabilities on DurableAgent", a fix was implemented to introduce an onWorkflowCompletion callback. The related PR [#279](https://github.com/dapr/dapr-agents/pull/279) merged modifications for handling final outputs in a streamlined manner.
