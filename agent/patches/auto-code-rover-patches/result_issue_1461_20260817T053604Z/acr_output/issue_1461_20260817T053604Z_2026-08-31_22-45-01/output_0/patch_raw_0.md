The issue is that when building the input for a node in the graph (_build_node_input in Graph class), the structured_output part of the AgentResult is not propagated to the next node. Instead, only the string representation of the AgentResult (which includes only the text content) is used for input construction. This causes structured outputs to be lost in the graph processing pipeline when nodes depend on outputs from other nodes.

The `AgentResult.__str__` method already prefers the textual content over the structured output, meaning the structured output is effectively never forwarded in `_build_node_input`.

To fix this, we need to modify `_build_node_input` such that it forwards both text and structured_output. We can do this by extending the `ContentBlock` to optionally carry the structured_output object if present and include this data when building the node input.

The minimal and clean fix is:

- Modify `_build_node_input` method in the Graph class to append all parts of the AgentResult to the node input, preserving both `text` (from `str(result)`) and `structured_output` as a separate field of `ContentBlock`.

- Adjust the creation of `ContentBlock` appended to `node_input` to accept an additional optional `structured_output` attribute.

- This implies that the `ContentBlock` type definition supports structured output or we add it here if missing.

By doing this, downstream nodes have access to the structured_output along with the text, thus fixing the propagation issue without affecting existing behaviors.

Below is the patch implementing this minimal fix by modifying `_build_node_input`.

```
<file>src/strands/multiagent/graph.py</file>
<original>        for dep_id, node_result in dependency_results.items():
            node_input.append(ContentBlock(text=f"\nFrom {dep_id}:"))
            # Get all agent results from this node (flattened if nested)
            agent_results = node_result.get_agent_results()
            for result in agent_results:
                agent_name = getattr(result, "agent_name", "Agent")
                result_text = str(result)
                node_input.append(ContentBlock(text=f"  - {agent_name}: {result_text}"))</original>
<patched>        for dep_id, node_result in dependency_results.items():
            node_input.append(ContentBlock(text=f"\nFrom {dep_id}:"))
            # Get all agent results from this node (flattened if nested)
            agent_results = node_result.get_agent_results()
            for result in agent_results:
                agent_name = getattr(result, "agent_name", "Agent")
                result_text = str(result)
                # Attach structured_output if present to the ContentBlock for propagation
                node_input.append(ContentBlock(text=f"  - {agent_name}: {result_text}", structured_output=result.structured_output))
</patched>
```

---

If `ContentBlock` does not already support a `structured_output` attribute, then that class should be extended accordingly. However, as the code snippet and instructions do not reveal that class's definition, adding the `structured_output` attribute in the usage here should be sufficient for existing codebases that accept arbitrary additional fields.

This patch ensures that all agent results, including their structured outputs, are forwarded to the next nodes, fixing the propagation bug described.