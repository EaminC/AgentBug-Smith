import pytest
from unittest.mock import Mock, MagicMock
from dapr_agents.tool.mcp.client import MCPClient
from dapr_agents.types.exceptions import ToolError


class MockContent:
    def __init__(self, text=None):
        self.text = text


class MockResult:
    def __init__(self, isError=False, content=None):
        self.isError = isError
        self.content = content

    def __str__(self):
        return f"<MockResult isError={self.isError}>"


def test_mcp_client_process_tool_result_no_content():
    """Test result without content attribute."""
    client = MCPClient()
    result = MockResult(isError=False, content=None)
    output = client._process_tool_result(result)
    assert output == str(result)


def test_mcp_client_process_tool_result_empty_content():
    """Test result with empty content list."""
    client = MCPClient()
    result = MockResult(isError=False, content=[])
    output = client._process_tool_result(result)
    assert output == str(result)


def test_mcp_client_process_tool_result_single_text_content():
    """Test result with single content item containing text."""
    client = MCPClient()
    content = [MockContent(text="Hello world")]
    result = MockResult(isError=False, content=content)
    output = client._process_tool_result(result)
    assert output == "Hello world"


def test_mcp_client_process_tool_result_multiple_text_content():
    """Test result with multiple content items containing text."""
    client = MCPClient()
    content = [MockContent(text="First"), MockContent(text="Second")]
    result = MockResult(isError=False, content=content)
    output = client._process_tool_result(result)
    assert output == ["First", "Second"]


def test_mcp_client_process_tool_result_content_without_text():
    """Test content without text attribute."""
    client = MCPClient()
    content = [Mock()]
    result = MockResult(isError=False, content=content)
    output = client._process_tool_result(result)
    # In buggy code, this would return the mock object's text attribute (which is a Mock)
    # In fixed code, since content has no text attribute, it should fall back to str(result)
    # Actually, the buggy code would also fall through to str(result) because it checks hasattr(content, 'text')
    # but the mock has a text attribute (Mock creates all attributes). So we need to ensure the mock doesn't have text.
    # Let's create a mock without text attribute.
    class NoTextMock:
        pass
    content = [NoTextMock()]
    result = MockResult(isError=False, content=content)
    output = client._process_tool_result(result)
    assert output == str(result)


def test_mcp_client_process_tool_result_error_with_content():
    """Test that when MCP server returns an error with content.text, the content is returned instead of raising ToolError."""
    client = MCPClient()

    # Simulate an error result that contains content with text
    error_content = [MockContent(text="Server error: invalid input")]
    result = MockResult(isError=True, content=error_content)

    # In buggy code, this would raise ToolError
    # In fixed code, this should return the text content
    output = client._process_tool_result(result)
    assert output == "Server error: invalid input"


def test_mcp_client_process_tool_result_error_with_content_no_text():
    """Test error result with content but no text attribute should raise ToolError."""
    client = MCPClient()
    # Create a mock without text attribute
    class NoTextMock:
        pass
    content = [NoTextMock()]
    result = MockResult(isError=True, content=content)

    # In buggy code, this would raise ToolError with "Unknown error"
    # In fixed code, since content has no text attribute, text_contents is empty,
    # then isError=True triggers, raising ToolError.
    with pytest.raises(ToolError, match="MCP tool error:"):
        client._process_tool_result(result)


def test_mcp_client_process_tool_result_error_with_multiple_content_one_text():
    """Test error result with multiple content items, one with text, returns text."""
    client = MCPClient()
    # First mock without text, second with text
    class NoTextMock:
        pass
    content = [NoTextMock(), MockContent(text="Error details")]
    result = MockResult(isError=True, content=content)
    output = client._process_tool_result(result)
    # Should return the text content, not raise ToolError
    assert output == "Error details"


def test_mcp_client_process_tool_result_error_without_content():
    """Test error result without content attribute raises ToolError."""
    client = MCPClient()
    result = MockResult(isError=True, content=None)
    with pytest.raises(ToolError, match="MCP tool error:"):
        client._process_tool_result(result)


def test_mcp_client_process_tool_result_error_with_empty_content():
    """Test error result with empty content list raises ToolError."""
    client = MCPClient()
    result = MockResult(isError=True, content=[])
    with pytest.raises(ToolError, match="MCP tool error:"):
        client._process_tool_result(result)
