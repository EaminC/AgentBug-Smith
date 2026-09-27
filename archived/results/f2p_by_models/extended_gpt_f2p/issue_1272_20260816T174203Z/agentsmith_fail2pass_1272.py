import pytest

from strands.session.repository_session_manager import RepositorySessionManager
from strands.session.repository_session_manager import SessionMessage


@pytest.fixture
def session_manager():
    from tests.fixtures.mock_session_repository import MockedSessionRepository

    mock_repo = MockedSessionRepository()
    return RepositorySessionManager(session_id="test-session", session_repository=mock_repo)


def test_fix_broken_tool_use_removes_orphaned_tool_result_at_start(session_manager):
    """Test that orphaned toolResult at the start of conversation is removed."""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "orphaned-result-123",
                        "status": "success",
                        "content": [{"text": "Seattle, USA"}],
                    }
                }
            ],
        },
        {"role": "assistant", "content": [{"text": "You live in Seattle, USA."}]},
        {"role": "user", "content": [{"text": "I like pizza"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(messages)

    # Should remove the first message with orphaned toolResult
    assert len(fixed_messages) == 2
    assert fixed_messages[0]["role"] == "assistant"
    assert fixed_messages[0]["content"][0]["text"] == "You live in Seattle, USA."
    assert fixed_messages[1]["role"] == "user"
    assert fixed_messages[1]["content"][0]["text"] == "I like pizza"


def test_fix_broken_tool_use_does_not_affect_normal_conversations(session_manager):
    """Test that normal conversations without orphaned toolResults are unaffected."""
    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(messages)

    # Should remain unchanged
    assert fixed_messages == messages


def test_fix_broken_tool_use_handles_orphaned_tool_use_and_result(session_manager):
    """Test that orphaned toolUse messages missing toolResult and orphaned toolResult messages missing toolUse are fixed correctly."""
    # Messages simulating the bug scenario:
    # The first message is a user message with a toolResult but no preceding toolUse (should be removed)
    # The second message is assistant with toolUse without toolResult (should add missing toolResult)
    # The third message is user with toolResult matching the first toolUse (valid)
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tooluse_001",
                        "status": "success",
                        "content": [{"text": "Result without use"}],
                    }
                }
            ],
        },
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tooluse_002",
                        "name": "test_tool",
                        "input": {"input": "test input"},
                    }
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tooluse_002",
                        "status": "success",
                        "content": [{"text": "Result for tooluse_002"}],
                    }
                }
            ],
        },
    ]

    fixed_messages = session_manager._fix_broken_tool_use(messages)

    # The first message with orphaned toolResult should be removed
    # The second message should remain with toolUse
    # No new message inserted because toolResult for tooluse_002 exists
    # So total messages should be 2 after fix
    assert len(fixed_messages) == 2

    # The first message now should be the assistant message with toolUse
    assert fixed_messages[0]["role"] == "assistant"
    assert any("toolUse" in c for c in fixed_messages[0]["content"])

    # The second message should be the user message with toolResult for tooluse_002
    assert fixed_messages[1]["role"] == "user"
    assert any(
        "toolResult" in c and c["toolResult"]["toolUseId"] == "tooluse_002"
        for c in fixed_messages[1]["content"]
    )


def test_fix_broken_tool_use_inserts_missing_tool_result(session_manager):
    """Test that missing toolResult messages are inserted after orphaned toolUse messages."""
    messages = [
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tooluse_100",
                        "name": "test_tool",
                        "input": {"input": "test input"},
                    }
                }
            ],
        },
        {"role": "user", "content": [{"text": "Next user message"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(messages)

    # Should insert a new message with toolResult for tooluse_100 between the two messages
    assert len(fixed_messages) == 3

    # The inserted message should be at index 1 and contain toolResult for tooluse_100
    inserted_message = fixed_messages[1]
    assert inserted_message["role"] == "user"
    assert any(
        "toolResult" in c and c["toolResult"]["toolUseId"] == "tooluse_100"
        for c in inserted_message["content"]
    )
    # The status should be "error" and content text "Tool was interrupted."
    tool_result = next(
        c["toolResult"] for c in inserted_message["content"] if "toolResult" in c
    )
    assert tool_result["status"] == "error"
    assert tool_result["content"] == [{"text": "Tool was interrupted."}]


def test_fix_broken_tool_use_does_not_fix_last_message_tool_use(session_manager):
    """Test that orphaned toolUse in the last message is not fixed."""
    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "last-message-123", "name": "test_tool", "input": {"input": "test"}}}
            ],
        },
    ]

    fixed_messages = session_manager._fix_broken_tool_use(messages)

    # Should remain unchanged since toolUse is in last message
    assert fixed_messages == messages
