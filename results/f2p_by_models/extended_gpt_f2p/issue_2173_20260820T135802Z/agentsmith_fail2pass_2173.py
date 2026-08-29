import pytest

from strands.agent.conversation_manager.sliding_window_conversation_manager import SlidingWindowConversationManager
from strands.types.exceptions import ContextWindowOverflowException
from strands.agent.agent import Agent


@pytest.mark.xfail(strict=True)
def test_sliding_window_tool_heavy_conversation_fails_to_trim_before_fix():
    """This test reproduces the bug: reduce_context raises ContextWindowOverflowException on tool-heavy conversation."""
    manager = SlidingWindowConversationManager(window_size=4, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "Review this PR"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "get_diff", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": "diff data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "2", "name": "get_file", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "2", "content": [{"text": "file data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "3", "name": "get_tree", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "3", "content": [{"text": "tree data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"text": "Here is my review"}]},
    ]
    test_agent = Agent(messages=messages)

    with pytest.raises(ContextWindowOverflowException):
        manager.reduce_context(test_agent, e=Exception("context window overflow"))


def test_sliding_window_tool_heavy_conversation_trims_after_fix():
    """This test verifies that after the fix, reduce_context trims tool-heavy conversations successfully."""
    manager = SlidingWindowConversationManager(window_size=4, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "Review this PR"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "get_diff", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": "diff data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "2", "name": "get_file", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "2", "content": [{"text": "file data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "3", "name": "get_tree", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "3", "content": [{"text": "tree data"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"text": "Here is my review"}]},
    ]
    test_agent = Agent(messages=messages)

    # After fix, reduce_context should NOT raise and should trim messages
    manager.reduce_context(test_agent, e=Exception("context window overflow"))

    # The messages should be trimmed to a smaller size
    assert len(messages) < 8
    # The first message after trimming should be either a user message or an assistant(toolUse) message followed by user(toolResult)
    first_msg = messages[0]
    assert first_msg["role"] in ("user", "assistant")
    if first_msg["role"] == "assistant":
        # It must have toolUse content
        assert any("toolUse" in content for content in first_msg["content"])
        # The next message must be user with toolResult content
        assert len(messages) > 1
        next_msg = messages[1]
        assert next_msg["role"] == "user"
        assert any("toolResult" in content for content in next_msg["content"])
    else:
        # If first message is user, it must not contain toolResult (plain user message)
        assert not any("toolResult" in content for content in first_msg["content"])


def test_sliding_window_prefers_plain_user_message_over_tool_pair_fallback():
    """Plain user messages are preferred over assistant+toolResult fallback when both exist."""
    manager = SlidingWindowConversationManager(window_size=2, should_truncate_results=False)
    messages = [
        {"role": "user", "content": [{"text": "First"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "tool1", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": "result"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"text": "Response"}]},
        {"role": "user", "content": [{"text": "Plain user message"}]},
        {"role": "assistant", "content": [{"text": "Final response"}]},
    ]
    test_agent = Agent(messages=messages)

    manager.apply_management(test_agent)

    # Should prefer the plain user message, not the assistant+toolResult fallback
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == [{"text": "Plain user message"}]
