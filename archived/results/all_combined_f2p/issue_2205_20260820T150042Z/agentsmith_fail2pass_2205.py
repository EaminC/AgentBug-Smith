from strands.agent.agent import Agent
from strands.agent.conversation_manager.sliding_window_conversation_manager import SlidingWindowConversationManager
import pytest


def test_window_size_negative_raises_value_error():
    with pytest.raises(ValueError, match="window_size"):
        SlidingWindowConversationManager(window_size=-1)


def test_window_size_zero_clears_all_messages_on_apply_management():
    """window_size=0 should remove all messages, matching TypeScript SDK behaviour (issue #2205)."""
    manager = SlidingWindowConversationManager(window_size=0, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there"}]},
    ]
    test_agent = Agent(messages=messages)
    manager.apply_management(test_agent)

    assert messages == []
    assert manager.removed_message_count == 2


def test_window_size_zero_clears_all_messages_on_reduce_context():
    """reduce_context with window_size=0 should clear all messages even without overflow."""
    manager = SlidingWindowConversationManager(window_size=0, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "First"}]},
        {"role": "assistant", "content": [{"text": "Second"}]},
        {"role": "user", "content": [{"text": "Third"}]},
    ]
    test_agent = Agent(messages=messages)
    manager.reduce_context(test_agent)

    assert messages == []
    assert manager.removed_message_count == 3


def test_window_size_zero_clears_on_overflow():
    """reduce_context with window_size=0 should clear messages even when called with an overflow exception."""
    manager = SlidingWindowConversationManager(window_size=0, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi"}]},
    ]
    test_agent = Agent(messages=messages)
    manager.reduce_context(test_agent, e=Exception("overflow"))

    assert messages == []
