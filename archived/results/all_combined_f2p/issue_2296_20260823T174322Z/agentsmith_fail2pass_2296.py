import copy
import pytest

from strands.agent.agent import Agent
from strands.session.repository_session_manager import RepositorySessionManager
from strands.types.session import SessionMessage


@pytest.fixture
def session_manager():
    # Create a RepositorySessionManager with a fresh in-memory mock repository
    # We avoid importing tests.fixtures.mock_session_repository to prevent ImportError
    # Instead, create a minimal mock repository inline
    class InMemorySessionRepository:
        def __init__(self):
            self.sessions = {}
            self.agents = {}
            self.messages = {}

        def read_session(self, session_id):
            return self.sessions.get(session_id)

        def create_session(self, session):
            self.sessions[session.session_id] = session

        def read_agent(self, session_id, agent_id):
            return self.agents.get((session_id, agent_id))

        def create_agent(self, session_id, session_agent):
            self.agents[(session_id, session_agent.agent_id)] = session_agent

        def create_message(self, session_id, agent_id, message):
            self.messages.setdefault((session_id, agent_id), []).append(message)

        def list_messages(self, session_id, agent_id):
            return self.messages.get((session_id, agent_id), [])

    # Create a dummy Session and SessionAgent class to satisfy RepositorySessionManager
    from strands.types.session import Session, SessionAgent, SessionType

    repo = InMemorySessionRepository()
    # Create session explicitly to avoid creating twice
    session = Session(session_id="test-session", session_type=SessionType.AGENT)
    repo.create_session(session)

    manager = RepositorySessionManager(session_id="test-session", session_repository=repo)
    return manager


def test_fix_broken_tool_use_removes_stale_tool_results(session_manager):
    """Test that toolResults with IDs not matching any preceding toolUse are dropped (#2296)."""
    messages = [
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "valid-123", "name": "test_tool", "input": {"input": "test"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "stale-999", "status": "success", "content": [{"text": "stale"}]}},
                {"toolResult": {"toolUseId": "valid-123", "status": "success", "content": [{"text": "result"}]}},
            ],
        },
        {"role": "user", "content": [{"text": "Final message"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(copy.deepcopy(messages))

    # The stale toolResult should be removed, only valid toolResult remains
    assert len(fixed_messages) == 3
    # The second message content should only contain the valid toolResult
    assert fixed_messages[1]["content"] == [
        {"toolResult": {"toolUseId": "valid-123", "status": "success", "content": [{"text": "result"}]}}
    ]

    # The rest of the messages should be unchanged
    assert fixed_messages[0] == messages[0]
    assert fixed_messages[2] == messages[2]


def test_fix_broken_tool_use_adds_exact_number_of_tool_results(session_manager):
    """Test that the fix adds exactly one toolResult per toolUse, no extras."""

    messages = [
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tooluse-1", "name": "tool1", "input": {"input": "data1"}}},
                {"toolUse": {"toolUseId": "tooluse-2", "name": "tool2", "input": {"input": "data2"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                # Only one toolResult present, missing for tooluse-2
                {"toolResult": {"toolUseId": "tooluse-1", "status": "success", "content": [{"text": "result1"}]}},
            ],
        },
        {"role": "user", "content": [{"text": "Another message"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(copy.deepcopy(messages))

    # There should be exactly one toolResult per toolUse in the next message after assistant message
    # So second message content should have two toolResults, one existing success, one error for missing
    assert len(fixed_messages) == 3
    assert len(fixed_messages[1]["content"]) == 2

    tool_use_ids = {tr["toolResult"]["toolUseId"] for tr in fixed_messages[1]["content"]}
    assert tool_use_ids == {"tooluse-1", "tooluse-2"}

    # Check that tooluse-1 result is unchanged
    tr1 = next(tr for tr in fixed_messages[1]["content"] if tr["toolResult"]["toolUseId"] == "tooluse-1")
    assert tr1["toolResult"]["status"] == "success"
    assert tr1["toolResult"]["content"][0]["text"] == "result1"

    # Check that tooluse-2 result is error with correct text
    tr2 = next(tr for tr in fixed_messages[1]["content"] if tr["toolResult"]["toolUseId"] == "tooluse-2")
    assert tr2["toolResult"]["status"] == "error"
    assert tr2["toolResult"]["content"][0]["text"] == "Tool was interrupted."


def test_fix_broken_tool_use_does_not_add_extra_tool_results(session_manager):
    """Test that no extra toolResult blocks are added beyond the number of toolUse blocks."""

    messages = [
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tu-1", "name": "tool1", "input": {"input": "data"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tu-1", "status": "success", "content": [{"text": "result"}]}},
                # Extra toolResult that does not correspond to any toolUse
                {"toolResult": {"toolUseId": "extra-999", "status": "success", "content": [{"text": "extra"}]}},
            ],
        },
        {"role": "user", "content": [{"text": "End"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(copy.deepcopy(messages))

    # The extra toolResult should be removed, only one toolResult matching toolUse remains
    assert len(fixed_messages) == 3
    assert fixed_messages[1]["content"] == [
        {"toolResult": {"toolUseId": "tu-1", "status": "success", "content": [{"text": "result"}]}}
    ]


def test_fix_broken_tool_use_inserts_tool_result_message_when_missing(session_manager):
    """Test that if the next message after toolUse is not a toolResult message, one is inserted."""

    messages = [
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tu-1", "name": "tool1", "input": {"input": "data"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"text": "Some unrelated user message"},
            ],
        },
        {"role": "user", "content": [{"text": "End"}]},
    ]

    fixed_messages = session_manager._fix_broken_tool_use(copy.deepcopy(messages))

    # A new user message with toolResult should be inserted after the assistant message
    # So total messages increase by 1
    assert len(fixed_messages) == 4

    # The inserted message is at index 1
    inserted_message = fixed_messages[1]
    assert inserted_message["role"] == "user"
    # It should contain exactly one toolResult for the toolUse
    assert len(inserted_message["content"]) == 1
    tr = inserted_message["content"][0]
    assert "toolResult" in tr
    assert tr["toolResult"]["toolUseId"] == "tu-1"
    assert tr["toolResult"]["status"] == "error"
    assert tr["toolResult"]["content"][0]["text"] == "Tool was interrupted."

    # The original user message is shifted to index 2
    assert fixed_messages[2]["content"][0]["text"] == "Some unrelated user message"


def test_fix_broken_tool_use_leaves_last_tool_use_untouched(session_manager):
    """Test that toolUse in the last message is not fixed (no toolResult added)."""

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "last-123", "name": "tool", "input": {"input": "data"}}}
            ],
        },
    ]

    fixed_messages = session_manager._fix_broken_tool_use(copy.deepcopy(messages))

    # Should remain unchanged because last message with toolUse is not fixed here
    assert fixed_messages == messages
