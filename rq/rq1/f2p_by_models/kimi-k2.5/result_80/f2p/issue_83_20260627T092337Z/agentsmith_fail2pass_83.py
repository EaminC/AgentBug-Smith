import pytest
from dapr_agents.tool.mcp.client import MCPClient
from dapr_agents.types.exceptions import ToolError


class MockContent:
    def __init__(self, text):
        self.text = text


class MockResult:
    def __init__(self, is_error, content):
        self.isError = is_error
        self.content = content


def test_mcp_error_result_with_content_returns_text():
    """
    Test that when an MCP tool returns an error result containing content with text,
    the _process_tool_result method returns the text content instead of raising ToolError.
    
    This verifies the fix for issue #83 where error content was lost because ToolError
    was raised before extracting the content text.
    """
    client = MCPClient()
    
    # Create a mock result simulating an MCP error response with text content
    mock_content = MockContent("Division by zero in calculation")
    mock_result = MockResult(is_error=True, content=[mock_content])
    
    # Buggy behavior: raises ToolError, so content is lost and test fails with exception
    # Fixed behavior: returns the text content so model can iterate on the error
    result = client._process_tool_result(mock_result)
    
    assert result == "Division by zero in calculation"
