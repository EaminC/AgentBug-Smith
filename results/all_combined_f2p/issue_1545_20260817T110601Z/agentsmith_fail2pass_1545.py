import pytest

from strands.agent.agent import Agent
from strands.agent.conversation_manager.sliding_window_conversation_manager import SlidingWindowConversationManager
from strands.types.content import Messages


def test_truncation_targets_oldest_message_first():
    """Oldest message with tool results is truncated before newer ones."""
    large_text = "X" * 20000
    manager = SlidingWindowConversationManager(window_size=10)
    messages = [
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "1", "name": "tool1", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": large_text}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "2", "name": "tool2", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "2", "content": [{"text": large_text}], "status": "success"}}],
        },
    ]
    test_agent = Agent(messages=messages)

    manager.reduce_context(test_agent)

    # The oldest tool result (index 1) must be truncated
    oldest_text = messages[1]["content"][0]["toolResult"]["content"][0]["text"]
    assert "... [truncated:" in oldest_text

    # The newest tool result (index 3) must remain untouched after the first reduce_context call
    newest_text = messages[3]["content"][0]["toolResult"]["content"][0]["text"]
    assert "... [truncated:" not in newest_text


def test_large_tool_result_partially_truncated_with_context_preserved():
    """Large tool results are truncated in the middle while the beginning and end are preserved."""
    preserve = 200  # matches _PRESERVE_CHARS
    # Build text with distinct prefix, middle, and suffix
    prefix_text = "P" * preserve
    middle_text = "M" * 500
    suffix_text = "S" * preserve
    large_text = prefix_text + middle_text + suffix_text

    manager = SlidingWindowConversationManager(window_size=10)
    messages = [
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": large_text}], "status": "success"}}],
        }
    ]

    truncated = manager._truncate_tool_results(messages, 0)

    assert truncated
    result_text = messages[0]["content"][0]["toolResult"]["content"][0]["text"]
    assert result_text.startswith(prefix_text)
    assert result_text.endswith(suffix_text)
    assert "... [truncated:" in result_text
    removed = len(large_text) - 2 * preserve
    assert f"... [truncated: {removed} chars removed] ..." in result_text


def test_truncation_does_not_change_status_to_error():
    """Partial truncation must not change the tool result status."""
    large_text = "Z" * 15000
    manager = SlidingWindowConversationManager(window_size=10)
    messages = [
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": large_text}], "status": "success"}}],
        }
    ]

    manager._truncate_tool_results(messages, 0)

    # Status must remain 'success' after truncation
    assert messages[0]["content"][0]["toolResult"]["status"] == "success"


def test_image_blocks_inside_tool_result_replaced_with_placeholder():
    """Image blocks nested inside toolResult content are replaced with a text placeholder."""
    manager = SlidingWindowConversationManager(window_size=10)
    image_data = b"base64encodeddata"
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "1",
                        "content": [
                            {"text": "some text"},
                            {
                                "image": {
                                    "format": "jpeg",
                                    "source": {"bytes": image_data},
                                }
                            },
                        ],
                        "status": "success",
                    }
                }
            ],
        }
    ]

    changed = manager._truncate_tool_results(messages, 0)

    assert changed
    tool_result_items = messages[0]["content"][0]["toolResult"]["content"]
    # No image blocks remain
    assert not any(isinstance(item, dict) and "image" in item for item in tool_result_items)
    expected_placeholder = f"[image: jpeg, {len(image_data)} bytes]"
    # Placeholder text block is present
    assert any(isinstance(item, dict) and item.get("text") == expected_placeholder for item in tool_result_items)


def test_already_truncated_text_not_truncated_again():
    """A text block that already contains the truncation marker is not truncated a second time."""
    manager = SlidingWindowConversationManager(window_size=10)
    already_truncated = "A" * 200 + "...\n\n... [truncated: 990 chars removed] ...\n\n..." + "Z" * 200
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "1",
                        "content": [{"text": already_truncated}],
                        "status": "success",
                    }
                }
            ],
        }
    ]

    changed = manager._truncate_tool_results(messages, 0)

    assert not changed
    assert messages[0]["content"][0]["toolResult"]["content"][0]["text"] == already_truncated


def test_short_text_in_tool_result_not_truncated():
    """Text no longer than 2 * _PRESERVE_CHARS must not be modified."""
    manager = SlidingWindowConversationManager(window_size=10)
    short_text = "X" * 100  # 100 < 2 * 200
    messages = [
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": short_text}], "status": "success"}}],
        }
    ]

    changed = manager._truncate_tool_results(messages, 0)

    assert not changed
    assert messages[0]["content"][0]["toolResult"]["content"][0]["text"] == short_text


def test_boundary_text_in_tool_result_not_truncated():
    """Text of exactly 2 * _PRESERVE_CHARS must not be truncated."""
    manager = SlidingWindowConversationManager(window_size=10)
    boundary_text = "X" * 400  # exactly 2 * 200
    messages = [
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "1", "content": [{"text": boundary_text}], "status": "success"}}],
        }
    ]

    changed = manager._truncate_tool_results(messages, 0)

    assert not changed
    assert messages[0]["content"][0]["toolResult"]["content"][0]["text"] == boundary_text


def test_per_turn_zero_raises_value_error():
    with pytest.raises(ValueError, match="per_turn"):
        SlidingWindowConversationManager(per_turn=0)


def test_per_turn_negative_raises_value_error():
    with pytest.raises(ValueError, match="per_turn"):
        SlidingWindowConversationManager(per_turn=-5)
