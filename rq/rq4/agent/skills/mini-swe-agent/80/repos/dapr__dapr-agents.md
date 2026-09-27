# Repo identity
The repository `dapr-agents` is designed to simplify agentic workflows, focusing on various agent interactions within a system. The codebase is predominantly written in Python and maintained by the Dapr Authors. The project enables the execution of complex workflows and integration with various agent patterns commonly used in distributed systems.

# Typical issue shape
- Issues typically include bug reports, feature requests, and enhancements focusing on agent behaviors and interactions.
- Many reports are well-specified and provide reproduction steps, often linked with example cases or quickstart guides.
- Issues can be tagged with categories like "bug" or "enhancement," aiding in prioritizing fixes and features.

# Recurring fix patterns
- When `os.Exit()` is called in a workflow, fix usually involves removing that call to prevent app termination in `dapr_agents/agents/orchestrators/base.py`.
- Issues with callbacks for workflow completion often get resolved by introducing a new callback method, e.g., adding an `onWorkflowCompletion` callback in `dapr_agents/agents/orchestrators/base.py`.
- When handling tool results from the MCP server, check if `result.content` has text; if not, throw a `ToolError`. Changes often happen in `dapr_agents/tool/mcp/client.py`.
- Improving concurrent workflow execution by ensuring no blocking via locks; modifications generally occur in `dapr_agents/workflow/runners/base.py`.

# Files / modules that change most often
| `<path>`                                   | `<why it gets touched>`                                                                     |
|--------------------------------------------|---------------------------------------------------------------------------------------------|
| `dapr_agents/agents/orchestrators/base.py` | To implement callback functionalities for workflow completions.                           |
| `dapr_agents/tool/mcp/client.py`           | To refine content extraction from tool responses and error handling mechanisms.            |
| `dapr_agents/workflow/runners/base.py`     | To enhance concurrency in workflow executions.                                             |
| `quickstarts/06_workflow_agents.py`        | For modifications in testing workflow agent functionalities and their interactions.       |

# Pitfalls
- Be cautious of synchronizing workflows; using locks can lead to undesirable blocking behaviors.
- Forgetting to handle exceptions on tool results can lead to missing important output data.
- Not updating related components when changing one part of the agent's workflow can cause cascading issues.

# Test conventions
Tests are stored under the `tests/` directory and are typically invoked using a testing framework like `pytest`. Tests often use filenames that hint at their purpose and are named with the convention `test_<feature_or_issue>.py`, facilitating easy identification and execution.

# One concrete worked example
For issue [#563](https://github.com/dapr/dapr-agents/issues/563), it was reported that the orchestrator agent only allows one active run at a time, leading to blocked executions. The fix was executed by removing a lock in the workflow creation logic, found in `dapr_agents/workflow/runners/base.py`. The pull request [#564](https://github.com/dapr/dapr-agents/pull/564) includes the implemented changes.
