import pytest

from strands.agent.agent import Agent
from strands.session.repository_session_manager import RepositorySessionManager
from strands.types.exceptions import SessionException
from tests.fixtures.mock_session_repository import MockedSessionRepository


def test_sync_agent_skips_update_when_state_not_dirty_and_internal_state_unchanged():
    """Test that sync_agent() skips update_agent() when state is not dirty and internal state unchanged."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # First sync should update (to establish baseline)
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1

    # Clear tracking
    update_agent_calls.clear()

    # Second sync without changes should skip update
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 0


def test_sync_agent_calls_update_when_state_is_dirty():
    """Test that sync_agent() calls update_agent() when agent.state is dirty."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # First sync to establish baseline
    session_manager.sync_agent(agent)
    update_agent_calls.clear()

    # Modify state (makes it dirty)
    agent.state.set("key", "value")

    # Sync should call update_agent because state is dirty
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1


def test_sync_agent_calls_update_when_internal_state_changed():
    """Test that sync_agent() calls update_agent() when internal state (interrupt_state) is dirty."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # First sync to establish baseline
    session_manager.sync_agent(agent)
    update_agent_calls.clear()

    # Modify internal state (activate interrupt state which sets dirty flag)
    agent._interrupt_state.activate()

    # Sync should call update_agent because internal state is dirty
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1


def test_sync_agent_calls_update_when_conversation_manager_state_changed():
    """Test that sync_agent() calls update_agent() when conversation manager state changed."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # First sync to establish baseline
    session_manager.sync_agent(agent)
    update_agent_calls.clear()

    # Modify conversation manager state
    agent.conversation_manager.removed_message_count = 5

    # Sync should call update_agent because conversation manager state changed
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1


def test_sync_agent_tracks_version_after_successful_sync():
    """Test that sync_agent() tracks version after successful sync."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # First sync to establish baseline
    session_manager.sync_agent(agent)
    initial_version = agent.state._get_version()

    # Modify state (increments version)
    agent.state.set("key", "value")
    assert agent.state._get_version() == initial_version + 1

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # Sync should update because version changed
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1

    # Second sync without changes should skip
    update_agent_calls.clear()
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 0


def test_sync_agent_retries_on_failure():
    """Test that sync_agent() retries on next call if update_agent() fails."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # First sync to establish baseline
    session_manager.sync_agent(agent)

    # Modify state (increments version)
    agent.state.set("key", "value")

    # Make update_agent fail
    def failing_update_agent(session_id, session_agent):
        raise SessionException("Update failed")

    mock_repository.update_agent = failing_update_agent

    # Sync should fail
    with pytest.raises(SessionException, match="Update failed"):
        session_manager.sync_agent(agent)

    # Restore working update_agent
    update_agent_calls = []
    original_update_agent = MockedSessionRepository.update_agent

    def tracking_update_agent(self, session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(self, session_id, session_agent)

    mock_repository.update_agent = lambda sid, sa: tracking_update_agent(mock_repository, sid, sa)

    # Retry should work because version wasn't updated on failure
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1


def test_sync_agent_first_sync_always_updates():
    """Test that the first sync_agent() call always updates (no previous state to compare)."""
    mock_repository = MockedSessionRepository()
    session_manager = RepositorySessionManager(session_id="test-session", session_repository=mock_repository)

    # Create and initialize agent
    agent = Agent(agent_id="test-agent", session_manager=session_manager)

    # Track update_agent calls
    update_agent_calls = []
    original_update_agent = mock_repository.update_agent

    def tracking_update_agent(session_id, session_agent):
        update_agent_calls.append((session_id, session_agent))
        return original_update_agent(session_id, session_agent)

    mock_repository.update_agent = tracking_update_agent

    # First sync should always update (no previous state)
    session_manager.sync_agent(agent)
    assert len(update_agent_calls) == 1
