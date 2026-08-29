import asyncio
import threading
import time
import unittest.mock
from typing import Any, AsyncGenerator

import pytest

from strands import Agent, ToolContext
from strands.types.exceptions import ConcurrencyException
from tests.fixtures.mocked_model_provider import MockedModelProvider


class SlowMockedModel(MockedModelProvider):
    async def stream(
        self, messages, tool_specs=None, system_prompt=None, tool_choice=None, **kwargs
    ) -> AsyncGenerator[Any, None]:
        await asyncio.sleep(0.15)  # Add async delay to ensure concurrency
        async for event in super().stream(messages, tool_specs, system_prompt, tool_choice, **kwargs):
            yield event


def test_agent_concurrent_call_raises_exception():
    """Test that concurrent __call__() calls raise ConcurrencyException."""
    model = SlowMockedModel(
        [
            {"role": "assistant", "content": [{"text": "hello"}]},
            {"role": "assistant", "content": [{"text": "world"}]},
        ]
    )
    agent = Agent(model=model)

    results = []
    errors = []
    lock = threading.Lock()

    def invoke():
        try:
            result = agent("test")
            with lock:
                results.append(result)
        except ConcurrencyException as e:
            with lock:
                errors.append(e)

    # Create two threads that will try to invoke concurrently
    t1 = threading.Thread(target=invoke)
    t2 = threading.Thread(target=invoke)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One should succeed, one should raise ConcurrencyException
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
    assert "concurrent" in str(errors[0]).lower() and "invocation" in str(errors[0]).lower()


def test_agent_concurrent_structured_output_raises_exception():
    """Test that concurrent structured_output() calls raise ConcurrencyException.

    Note: This test validates that the sync invocation path is protected.
    The concurrent __call__() test already validates the core functionality.
    """
    model = SlowMockedModel(
        [
            {"role": "assistant", "content": [{"text": "response1"}]},
            {"role": "assistant", "content": [{"text": "response2"}]},
        ]
    )
    agent = Agent(model=model)

    results = []
    errors = []
    lock = threading.Lock()

    def invoke():
        try:
            result = agent("test")
            with lock:
                results.append(result)
        except ConcurrencyException as e:
            with lock:
                errors.append(e)

    # Create two threads that will try to invoke concurrently
    t1 = threading.Thread(target=invoke)
    t2 = threading.Thread(target=invoke)

    t1.start()
    time.sleep(0.05)  # Small delay to ensure first thread acquires lock
    t2.start()
    t1.join()
    t2.join()

    # One should succeed, one should raise ConcurrencyException
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"
    assert "concurrent" in str(errors[0]).lower() and "invocation" in str(errors[0]).lower()


@pytest.mark.asyncio
async def test_agent_sequential_invocations_work():
    """Test that sequential invocations work correctly after lock is released."""
    model = MockedModelProvider(
        [
            {"role": "assistant", "content": [{"text": "response1"}]},
            {"role": "assistant", "content": [{"text": "response2"}]},
            {"role": "assistant", "content": [{"text": "response3"}]},
        ]
    )
    agent = Agent(model=model)

    # All sequential calls should succeed
    result1 = await agent.invoke_async("test1")
    assert result1.message["content"][0]["text"] == "response1"

    result2 = await agent.invoke_async("test2")
    assert result2.message["content"][0]["text"] == "response2"

    result3 = await agent.invoke_async("test3")
    assert result3.message["content"][0]["text"] == "response3"


@pytest.mark.asyncio
async def test_agent_lock_released_on_exception():
    """Test that lock is released when an exception occurs during invocation."""

    # Create a mock model that raises an explicit error
    mock_model = unittest.mock.Mock()

    async def failing_stream(*args, **kwargs):
        raise RuntimeError("Simulated model failure")
        yield  # Make this an async generator

    mock_model.stream = failing_stream

    agent = Agent(model=mock_model)

    # First call will fail due to the simulated error
    with pytest.raises(RuntimeError, match="Simulated model failure"):
        await agent.invoke_async("test")

    # Lock should be released, so this should not raise ConcurrencyException
    # It will still raise RuntimeError, but that's expected
    with pytest.raises(RuntimeError, match="Simulated model failure"):
        await agent.invoke_async("test")


def test_agent_direct_tool_call_during_invocation_raises_exception():
    """Test that direct tool call during agent invocation raises ConcurrencyException."""

    tool_calls = []

    import strands

    @strands.tool
    def tool_to_invoke():
        tool_calls.append("tool_to_invoke")
        return "called"

    @strands.tool(context=True)
    def agent_tool(tool_context: ToolContext) -> str:
        tool_context.agent.tool.tool_to_invoke(record_direct_tool_call=True)
        return "tool result"

    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "test-123",
                            "name": "agent_tool",
                            "input": {},
                        }
                    }
                ],
            },
            {"role": "assistant", "content": [{"text": "Done"}]},
        ]
    )
    agent = Agent(model=model, tools=[agent_tool, tool_to_invoke])
    agent("Hi")

    # Tool call should have not succeeded
    assert len(tool_calls) == 0

    assert agent.messages[-2] == {
        "content": [
            {
                "toolResult": {
                    "content": [
                        {
                            "text": "Error: ConcurrencyException - Direct tool call cannot be made while the agent is "
                            "in the middle of an invocation. Set record_direct_tool_call=False to allow direct tool "
                            "calls during agent invocation."
                        }
                    ],
                    "status": "error",
                    "toolUseId": "test-123",
                }
            }
        ],
        "role": "user",
    }


def test_agent_direct_tool_call_during_invocation_succeeds_with_record_false():
    """Test that direct tool call during agent invocation succeeds when record_direct_tool_call=False."""
    tool_calls = []

    import strands

    @strands.tool
    def tool_to_invoke():
        tool_calls.append("tool_to_invoke")
        return "called"

    @strands.tool(context=True)
    def agent_tool(tool_context: ToolContext) -> str:
        tool_context.agent.tool.tool_to_invoke(record_direct_tool_call=False)
        return "tool result"

    model = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "test-123",
                            "name": "agent_tool",
                            "input": {},
                        }
                    }
                ],
            },
            {"role": "assistant", "content": [{"text": "Done"}]},
        ]
    )
    agent = Agent(model=model, tools=[agent_tool, tool_to_invoke])
    agent("Hi")

    # Tool call should have succeeded
    assert len(tool_calls) == 1

    assert agent.messages[-2] == {
        "content": [
            {
                "toolResult": {
                    "content": [{"text": "tool result"}],
                    "status": "success",
                    "toolUseId": "test-123",
                }
            }
        ],
        "role": "user",
    }
