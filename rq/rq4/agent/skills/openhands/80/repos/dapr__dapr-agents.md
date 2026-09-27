
# Repo Identity
**Repository Name**: Dapr Agents
**Homepage**: [Dapr Agents Homepage](https://github.com/dapr/dapr-agents)
**Issue Tracker**: [Issues](https://github.com/dapr/dapr-agents/issues)

# Typical Issue Shape
Dapr Agents typically encounters issues related to agent workflows, including:
- Errors in tool invocation and output handling that prevent workflows from completing.
- Concurrency issues with the orchestration of multiple agent runs.
- The need for enhancements to facilitate programmatic callbacks upon workflow completion.
# Recurring Fix Patterns
Common fixes include:
- Modifying error handling logic to ensure that tool outputs are returned even in case of errors.
- Adjusting concurrency settings to allow multiple workflows to run simultaneously without blocking.

# Files / Modules that Change Most Often
The following files are frequently updated:
- `dapr_agents/workflow/runners/base.py`
- `dapr_agents/agents/orchestrators/base.py`
- `dapr_agents/tool/mcp/client.py`
# Pitfalls
Common pitfalls to avoid:
- Failing to handle tool outputs properly can lead to errors in workflows.
- Not considering concurrency can block agent processes, making them unresponsive.

# Test Conventions
Testing is often done using pytest, with specific tests for each workflow change. Tests are organized under the `tests` directory, and integration tests are particularly important for validating interactions across agents.
# One Concrete Worked Example
**Issue Title**: [Bug]: Content is always None when MCP server returns an 'error' to the client
**Issue Link**: [GitHub Issue #83](https://github.com/dapr/dapr-agents/issues/83)
**Description**: This issue highlighted that the error handling in the MCP client was not correctly returning useful information when the MCP server communicated an error. The fix required changing the error handling logic to ensure outputs could still be utilized for learning.
