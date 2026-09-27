import os
import asyncio
import pytest

from examples.agent.deep_research_agent.deep_research_agent import DeepResearchAgent
from src.agentscope.message import Msg


@pytest.mark.asyncio
async def test_deep_research_agent_avoids_attribute_error_on_none_metadata():
    """
    Test that DeepResearchAgent._acting does not raise AttributeError when chunk.metadata is None.
    This reproduces the bug described in issue #1476 and verifies it is fixed.

    The buggy code tries to call chunk.metadata.get("success") without checking if metadata is None,
    causing AttributeError. The fix adds a safe fallback to empty dict.

    The test constructs a minimal ToolUseBlock with an async generator that yields chunks with
    metadata=None, then calls _acting and asserts no exception is raised and the result is None.
    """

    # Create an instance of DeepResearchAgent with environment keys
    agent = DeepResearchAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    # Define a dummy async generator that yields chunks with metadata=None
    class DummyChunk:
        def __init__(self, metadata, is_last=False):
            self.metadata = metadata
            self.is_last = is_last

    async def dummy_tool_res():
        # Yield one chunk with metadata=None and is_last=False
        yield DummyChunk(metadata=None, is_last=False)
        # Yield one chunk with metadata=None and is_last=True
        yield DummyChunk(metadata=None, is_last=True)

    tool_call = {
        "name": "some_tool",
    }

    result = await agent._acting(tool_call=tool_call, tool_res=dummy_tool_res())

    assert result is None


@pytest.mark.asyncio
async def test_deep_research_agent_finish_function_with_none_metadata():
    """
    Test that DeepResearchAgent._acting returns response_msg correctly when chunk.metadata is None.

    This tests the branch where tool_call["name"] == finish_function_name and chunk.metadata.get("success")
    is checked safely when metadata is None.
    """

    agent = DeepResearchAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    class DummyChunk:
        def __init__(self, metadata, is_last=False):
            self.metadata = metadata
            self.is_last = is_last

    response_msg = Msg(content="dummy response")

    async def dummy_tool_res():
        yield DummyChunk(metadata=None, is_last=False)
        yield DummyChunk(metadata={"success": True, "response_msg": response_msg}, is_last=True)

    tool_call = {
        "name": agent.finish_function_name,
    }

    result = await agent._acting(tool_call=tool_call, tool_res=dummy_tool_res())

    assert result == response_msg


@pytest.mark.asyncio
async def test_deep_research_agent_update_memory_with_none_metadata():
    """
    Test that DeepResearchAgent._acting handles update_memory flag correctly when chunk.metadata is None.

    This tests the branch that checks chunk.metadata.get("update_memory") safely.
    """

    agent = DeepResearchAgent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    class DummyChunk:
        def __init__(self, metadata, is_last=False):
            self.metadata = metadata
            self.is_last = is_last

    async def dummy_tool_res():
        yield DummyChunk(metadata=None, is_last=False)
        yield DummyChunk(
            metadata={
                "update_memory": True,
                "intermediate_report": "some report",
            },
            is_last=True,
        )

    tool_call = {
        "name": "some_tool",
    }

    async def dummy_print(*args, **kwargs):
        pass

    agent.print = dummy_print

    result = await agent._acting(tool_call=tool_call, tool_res=dummy_tool_res())

    assert result is None
    assert isinstance(agent.current_subtask, list)


if __name__ == "__main__":
    asyncio.run(test_deep_research_agent_avoids_attribute_error_on_none_metadata())
    asyncio.run(test_deep_research_agent_finish_function_with_none_metadata())
    asyncio.run(test_deep_research_agent_update_memory_with_none_metadata())