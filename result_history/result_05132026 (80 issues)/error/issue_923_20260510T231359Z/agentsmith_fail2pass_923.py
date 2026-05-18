import os
import asyncio
import pytest

from agentscope.memory._mem0_utils import AgentScopeLLM


class DummyChatResponse:
    def __init__(self, content):
        self.content = content


@pytest.mark.asyncio
async def test_agent_scope_llm_parse_response_tool_and_text():
    # Prepare a dummy model response with mixed blocks including tool_use
    response_content = [
        {"type": "thinking", "thinking": "Calculating"},
        {"type": "text", "text": "The answer is 42."},
        {"type": "tool_use", "name": "calculator", "input": {"expression": "6*7"}},
    ]
    model_response = DummyChatResponse(response_content)

    llm = AgentScopeLLM(config=None)

    # Test with has_tool=True: should return dict with content and tool_calls keys
    parsed = llm._parse_response(model_response, has_tool=True)
    assert isinstance(parsed, dict)
    assert "content" in parsed
    assert "tool_calls" in parsed
    assert "[Thinking: Calculating]" in parsed["content"]
    assert "The answer is 42." in parsed["content"]
    assert any(tc.get("name") == "calculator" for tc in parsed["tool_calls"])

    # Test with has_tool=False: should return a string combining thinking and text blocks only
    parsed_no_tool = llm._parse_response(model_response, has_tool=False)
    assert isinstance(parsed_no_tool, str)
    assert "[Thinking: Calculating]" in parsed_no_tool
    assert "The answer is 42." in parsed_no_tool
    assert "calculator" not in parsed_no_tool


@pytest.mark.asyncio
async def test_generate_response_returns_correct_format(monkeypatch):
    # Patch AgentScopeLLM._acall to simulate async call returning DummyChatResponse
    dummy_response_content = [
        {"type": "thinking", "thinking": "Processing"},
        {"type": "text", "text": "Hello world."},
        {"type": "tool_use", "name": "search", "input": {"query": "Python"}},
    ]
    dummy_response = DummyChatResponse(dummy_response_content)

    async def dummy_acall(self, messages, tools=None):
        return dummy_response

    monkeypatch.setattr(AgentScopeLLM, "_acall", dummy_acall)

    llm = AgentScopeLLM(config=None)

    # Test with tools provided (has_tool=True)
    result = await llm.generate_response(
        messages=[{"role": "user", "content": "Hi"}],
        tools=[{"name": "search"}],
    )
    assert isinstance(result, dict)
    assert "content" in result
    assert "tool_calls" in result
    assert "[Thinking: Processing]" in result["content"]
    assert "Hello world." in result["content"]
    assert any(tc.get("name") == "search" for tc in result["tool_calls"])

    # Test with no tools (has_tool=False)
    result_no_tools = await llm.generate_response(
        messages=[{"role": "user", "content": "Hi"}],
        tools=None,
    )
    assert isinstance(result_no_tools, str)
    assert "[Thinking: Processing]" in result_no_tools
    assert "Hello world." in result_no_tools
    assert "search" not in result_no_tools


@pytest.mark.asyncio
async def test_generate_response_empty_content(monkeypatch):
    # Patch AgentScopeLLM._acall to simulate async call returning empty content
    dummy_response = DummyChatResponse(content=[])

    async def dummy_acall(self, messages, tools=None):
        return dummy_response

    monkeypatch.setattr(AgentScopeLLM, "_acall", dummy_acall)

    llm = AgentScopeLLM(config=None)

    # With tools (has_tool=True) should return dict with empty content and tool_calls
    result = await llm.generate_response(
        messages=[{"role": "user", "content": "Hello"}],
        tools=[{"name": "tool1"}],
    )
    assert isinstance(result, dict)
    assert result["content"] == ""
    assert result["tool_calls"] == []

    # Without tools (has_tool=False) should return empty string
    result_no_tools = await llm.generate_response(
        messages=[{"role": "user", "content": "Hello"}],
        tools=None,
    )
    assert result_no_tools == ""