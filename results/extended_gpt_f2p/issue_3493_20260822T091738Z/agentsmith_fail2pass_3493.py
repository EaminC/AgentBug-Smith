import asyncio
import pytest
from unittest.mock import MagicMock
from strands.vended_plugins.context_offloader import ContextOffloader, InMemoryStorage
from strands.types.tools import ToolUse


@pytest.mark.asyncio
async def test_retrieve_offloaded_content_error_status_for_missing_reference():
    storage = InMemoryStorage()
    plugin = ContextOffloader(storage=storage, max_result_tokens=25, preview_tokens=10, include_retrieval_tool=True)
    mock_agent = MagicMock()

    tool_use = ToolUse(toolUseId="retrieve_1", name="retrieve_offloaded_content", input={"reference": "nope"})
    events = [event async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": mock_agent})]
    result = events[-1].tool_result

    assert result["toolUseId"] == "retrieve_1"
    assert result["status"] == "error"
    assert "reference not found: nope" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_retrieve_offloaded_content_error_status_for_binary_content_search():
    storage = InMemoryStorage()
    plugin = ContextOffloader(storage=storage, max_result_tokens=25, preview_tokens=10, include_retrieval_tool=True)
    mock_agent = MagicMock()

    # Store binary content (image/png)
    ref = await storage.store("key_1", b"\x89PNG", "image/png")

    tool_use = ToolUse(
        toolUseId="retrieve_1",
        name="retrieve_offloaded_content",
        input={"reference": ref, "pattern": "test"},
    )
    events = [event async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": mock_agent})]
    result = events[-1].tool_result

    assert result["toolUseId"] == "retrieve_1"
    assert result["status"] == "error"
    assert "cannot search binary content (image/png)" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_retrieve_offloaded_content_error_status_for_out_of_range_line_range():
    storage = InMemoryStorage()
    plugin = ContextOffloader(storage=storage, max_result_tokens=25, preview_tokens=10, include_retrieval_tool=True)
    mock_agent = MagicMock()

    content = "line 1\nline 2"
    ref = await storage.store("key_1", content.encode("utf-8"), "text/plain")

    tool_use = ToolUse(
        toolUseId="retrieve_1",
        name="retrieve_offloaded_content",
        input={"reference": ref, "line_range": {"start": 100, "end": 200}},
    )
    events = [event async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": mock_agent})]
    result = events[-1].tool_result

    assert result["toolUseId"] == "retrieve_1"
    assert result["status"] == "error"
    assert "line_range.start (100) is beyond content length (2 lines)" in result["content"][0]["text"]


@pytest.mark.asyncio
async def test_retrieve_offloaded_content_success_status_for_valid_reference():
    storage = InMemoryStorage()
    plugin = ContextOffloader(storage=storage, max_result_tokens=25, preview_tokens=10, include_retrieval_tool=True)
    mock_agent = MagicMock()

    text = "hello world"
    ref = await storage.store("key_1", text.encode("utf-8"), "text/plain")

    tool_use = ToolUse(toolUseId="retrieve_1", name="retrieve_offloaded_content", input={"reference": ref})
    events = [event async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": mock_agent})]
    result = events[-1].tool_result

    assert result["toolUseId"] == "retrieve_1"
    assert result["status"] == "success"
    assert result["content"][0]["text"] == text


@pytest.mark.asyncio
async def test_retrieve_offloaded_content_success_status_for_search_with_no_matches():
    storage = InMemoryStorage()
    plugin = ContextOffloader(storage=storage, max_result_tokens=25, preview_tokens=10, include_retrieval_tool=True)
    mock_agent = MagicMock()

    text = "hello\nworld"
    ref = await storage.store("key_1", text.encode("utf-8"), "text/plain")

    tool_use = ToolUse(
        toolUseId="retrieve_1",
        name="retrieve_offloaded_content",
        input={"reference": ref, "pattern": "absent"},
    )
    events = [event async for event in plugin.retrieve_offloaded_content.stream(tool_use, {"agent": mock_agent})]
    result = events[-1].tool_result

    assert result["toolUseId"] == "retrieve_1"
    assert result["status"] == "success"
    assert "No matches found for pattern 'absent'" in result["content"][0]["text"]
