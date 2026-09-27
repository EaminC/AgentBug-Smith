from strands import Agent, ToolContext, tool


@tool(context=True)
def add_w_state(a: int, b: int, tool_context: ToolContext) -> int:
    result = a + b
    tool_context.agent.state.set("last_add_result", result)
    return result


def test_direct_tool_call_with_context_does_not_error():
    agent = Agent(tools=[add_w_state])
    result = agent.tool.add_w_state(a=1, b=1)
    # The result should be a dict with status success and content containing the sum as text
    assert isinstance(result, dict)
    assert result.get("status") == "success"
    content = result.get("content")
    assert isinstance(content, list)
    assert any("2" in block.get("text", "") for block in content if isinstance(block, dict))
    # The agent state should be updated with last_add_result = 2
    assert agent.state.get("last_add_result") == 2


@tool(context=True)
def calculate_sum(a: int, b: int, tool_context: ToolContext) -> int:
    result = a + b
    tool_context.agent.state.set("last_calculation", result)
    return result


def test_agent_state_access_through_tool_context():
    """Test that tools can access agent state through ToolContext."""
    agent = Agent(tools=[calculate_sum])
    result = agent.tool.calculate_sum(a=1, b=1)

    # Verify the tool executed successfully
    assert result["status"] == "success"

    # Verify the agent state was updated
    assert agent.state.get("last_calculation") == 2
