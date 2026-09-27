## Repo Identity
Repo name: langgraph

## Typical Issue Shape
Issues typically arise around runtime context not being passed correctly to subgraphs, leading to unexpected failures in agent execution.

## Recurring Fix Patterns
Common fixes involve modifying the graph construction to ensure proper context propagation from parent graphs to subgraph invocations.

## Files / Modules that Change Most Often
The following modules frequently see updates related to identified issues:
- libs/langgraph
- libs/checkpoint-conformance

## Pitfalls
A frequent pitfall is overlooking the context management within nested graphs, which can lead to runtime errors if not correctly handled.

## Test Conventions
Tests often use pytest and focus on verifying context handling across multiple execution flows.

## One Concrete Worked Example
### Title: Runtime context is not being passed to the subgraph
URL: [Issue 5700](https://github.com/langchain-ai/langgraph/issues/5700)
Details: Users reported that the context passed at the top level is not available in subgraph nodes, leading to execution failures. The issue provides a minimal reproduction example demonstrating the problem.

