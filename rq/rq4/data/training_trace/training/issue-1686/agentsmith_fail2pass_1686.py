import unittest.mock
import pytest

from strands import Agent
from strands.hooks import BeforeInvocationEvent, BeforeModelCallEvent, BeforeToolCallEvent
from tests.fixtures.mocked_model_provider import MockedModelProvider


def test_agent_add_hook_registers_callback():
    """Test that add_hook registers a callback with the hooks registry."""
    agent = Agent(model=MockedModelProvider([{"role": "assistant", "content": [{"text": "response"}]}]))
    callback = unittest.mock.Mock()

    agent.add_hook(callback, BeforeModelCallEvent)

    # Verify callback was registered by checking it gets invoked
    agent("test prompt")
    callback.assert_called_once()
    # Verify it was called with the correct event type
    call_args = callback.call_args[0]
    assert isinstance(call_args[0], BeforeModelCallEvent)


def test_agent_add_hook_delegates_to_hooks_add_callback():
    """Test that add_hook delegates to self.hooks.add_callback."""
    agent = Agent(model=MockedModelProvider([{"role": "assistant", "content": [{"text": "response"}]}]))
    callback = unittest.mock.Mock()

    # Spy on the hooks.add_callback method
    with unittest.mock.patch.object(agent.hooks, "add_callback") as mock_add_callback:
        agent.add_hook(callback, BeforeInvocationEvent)
        mock_add_callback.assert_called_once_with(BeforeInvocationEvent, callback)


@pytest.mark.asyncio
async def test_agent_add_hook_works_with_async_callback():
    """Test that add_hook works with async callbacks."""

    agent = Agent(model=MockedModelProvider([{"role": "assistant", "content": [{"text": "response"}]}]))
    async_callback = unittest.mock.AsyncMock()

    agent.add_hook(async_callback, BeforeModelCallEvent)

    # Use stream_async to invoke the agent with async support
    _ = [event async for event in agent.stream_async("test prompt")]
    async_callback.assert_called_once()
    # Verify it was called with the correct event type
    call_args = async_callback.call_args[0]
    assert isinstance(call_args[0], BeforeModelCallEvent)


def test_agent_add_hook_infers_event_type_from_callback():
    """Test that add_hook infers event type from callback type hint."""
    agent = Agent(model=MockedModelProvider([{"role": "assistant", "content": [{"text": "response"}]}]))
    callback_invoked = []

    def typed_callback(event: BeforeModelCallEvent) -> None:
        callback_invoked.append(event)

    agent.add_hook(typed_callback)
    agent("test prompt")

    assert len(callback_invoked) == 1
    assert isinstance(callback_invoked[0], BeforeModelCallEvent)


def test_agent_add_hook_raises_error_when_no_type_hint():
    """Test that add_hook raises error when event type cannot be inferred."""
    agent = Agent(model=MockedModelProvider([{"role": "assistant", "content": [{"text": "response"}]}]))

    def untyped_callback(event):
        pass

    with pytest.raises(ValueError, match="cannot infer event type"):
        agent.add_hook(untyped_callback)
