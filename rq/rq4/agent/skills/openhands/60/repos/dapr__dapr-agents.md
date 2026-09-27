## Repo Identity
Dapr Agents is a developer framework designed to build production-grade resilient AI agent systems that operate at scale. Built on top of the battle-tested Dapr project, it enables software developers to create AI agents that reason, act, and collaborate using Large Language Models (LLMs) while leveraging built-in observability and stateful workflow execution.
 
## Typical issue shape
Common issues usually involve errors in tool invocation and tool implementation. For example, issues can arise when tools fail to communicate properly, leading to errors that prevent the agent from functioning as expected.
 
## Recurring fix patterns
Recurring fixes often involve adjusting error handling logic within the MCP client to ensure that error messages are properly returned to the model for learning. Additionally, enhancing the resilience of workflows is a common adjustment made to avoid task failures.
 
## Files / modules that change most often
The modules that undergo the most frequent changes include `dapr_agents/tool/mcp/client.py` and various agent logic files that define core functionalities and workflows for the agents.
 
## Pitfalls
A common pitfall is the underestimation of error handling. Agents may enter failure loops if errors are not effectively communicated back through the system. Additionally, the complexity of multi-agent interactions can pose challenges in debugging.
 
## Test conventions
Testing conventions require that all issues should have corresponding test cases that validate the functionality and cover edge cases identified in bug reports. Automated tests in the `tests/` directory include unit and integration tests.
 
## One concrete worked example
### Issue Title: [Bug]: Content is always None when MCP server returns an \"error\" to the client
URL: [Issue 83](https://github.com/dapr/dapr-agents/issues/83)
The issue highlights a bug where the content returned is always None when an error occurs in the MCP server response. Adjustments were needed in error handling logic to ensure proper content is returned even in error scenarios.
