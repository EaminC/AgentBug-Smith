import os
import pytest
from dapr_agents.tool.mcp.client import MCPClient, ToolError


class DummyContent:
    def __init__(self, text):
        self.text = text


class DummyResult:
    def __init__(self, is_error=False, content=None):
        self.isError = is_error
        self.content = content


@pytest.fixture
def mcp_client():
    # Initialize MCPClient with environment variables if needed
    # Assuming MCPClient can be initialized without arguments or uses env vars internally
    return MCPClient()


def test_process_tool_result_with_error_and_content(mcp_client):
    # Simulate a result with isError=True but content with text present
    content = [DummyContent("Error message from MCP server")]
    result = DummyResult(is_error=True, content=content)

    # We expect the fixed code to return the text content, not raise ToolError
    result_content = mcp_client._process_tool_result(result)
    assert result_content == "Error message from MCP server"


def test_process_tool_result_with_error_no_content_raises(mcp_client):
    # Simulate a result with isError=True but no content or content without text
    result = DummyResult(is_error=True, content=None)

    with pytest.raises(ToolError) as excinfo:
        mcp_client._process_tool_result(result)
    assert "MCP tool error" in str(excinfo.value)


def test_process_tool_result_with_non_error_content(mcp_client):
    # Simulate a result with content but isError=False
    content = [DummyContent("Normal output from MCP server")]
    result = DummyResult(is_error=False, content=content)

    result_content = mcp_client._process_tool_result(result)
    assert result_content == "Normal output from MCP server"


def test_process_tool_result_with_multiple_contents(mcp_client):
    # Simulate a result with multiple content items
    content = [DummyContent("First output"), DummyContent("Second output")]
    result = DummyResult(is_error=False, content=content)

    result_content = mcp_client._process_tool_result(result)
    assert result_content == ["First output", "Second output"]


def test_process_tool_result_with_no_content_and_no_error(mcp_client):
    # Simulate a result with no content and no error
    result = DummyResult(is_error=False, content=None)

    result_content = mcp_client._process_tool_result(result)
    # Should fallback to str(result)
    assert result_content == str(result)