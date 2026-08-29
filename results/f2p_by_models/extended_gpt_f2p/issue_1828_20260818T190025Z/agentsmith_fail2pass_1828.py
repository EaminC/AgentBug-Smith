from unittest.mock import Mock

import pytest

from strands.agent.agent import Agent
from strands.agent.state import AgentState
from strands.session.repository_session_manager import RepositorySessionManager
from strands.types.session import Session, SessionType


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    from tests.fixtures.mock_session_repository import MockedSessionRepository

    return MockedSessionRepository()


@pytest.fixture
def existing_session_manager(mock_repository):
    """Create a session manager with a pre-existing session in the repository."""
    # Create session first so the manager sees it as existing
    session = Session(session_id="test-session", session_type=SessionType.AGENT)
    mock_repository.create_session(session)
    return RepositorySessionManager(session_id="test-session", session_repository=mock_repository)


def test_is_new_session_true_when_session_created(mock_repository):
    """Test that _is_new_session is True when creating a new session."""
    # Session doesn't exist yet
    assert mock_repository.read_session("new-session") is None

    # Creating manager should set _is_new_session to True
    manager = RepositorySessionManager(session_id="new-session", session_repository=mock_repository)

    assert manager._is_new_session is True


def test_is_new_session_false_when_session_exists(mock_repository):
    """Test that _is_new_session is False when using an existing session."""
    # Create session first
    session = Session(session_id="existing-session", session_type=SessionType.AGENT)
    mock_repository.create_session(session)

    # Creating manager should set _is_new_session to False
    manager = RepositorySessionManager(session_id="existing-session", session_repository=mock_repository)

    assert manager._is_new_session is False


def test_initialize_skips_read_agent_for_new_session(mock_repository):
    """Test that initialize() skips read_agent() call when _is_new_session is True."""
    # Create manager (new session)
    manager = RepositorySessionManager(session_id="new-session", session_repository=mock_repository)
    assert manager._is_new_session is True

    # Track read_agent calls
    read_agent_calls = []
    original_read_agent = mock_repository.read_agent

    def tracking_read_agent(session_id, agent_id):
        read_agent_calls.append((session_id, agent_id))
        return original_read_agent(session_id, agent_id)

    mock_repository.read_agent = tracking_read_agent

    # Initialize agent
    agent = Agent(agent_id="test-agent")
    manager.initialize(agent)

    # read_agent should NOT be called for new session
    assert len(read_agent_calls) == 0


def test_initialize_calls_read_agent_for_existing_session(mock_repository):
    """Test that initialize() calls read_agent() when _is_new_session is False."""
    # Create session first
    session = Session(session_id="existing-session", session_type=SessionType.AGENT)
    mock_repository.create_session(session)

    # Create manager (existing session)
    manager = RepositorySessionManager(session_id="existing-session", session_repository=mock_repository)
    assert manager._is_new_session is False

    # Track read_agent calls
    read_agent_calls = []
    original_read_agent = mock_repository.read_agent

    def tracking_read_agent(session_id, agent_id):
        read_agent_calls.append((session_id, agent_id))
        return original_read_agent(session_id, agent_id)

    mock_repository.read_agent = tracking_read_agent

    # Initialize agent
    agent = Agent(agent_id="test-agent")
    manager.initialize(agent)

    # read_agent should be called for existing session
    assert len(read_agent_calls) == 1
    assert read_agent_calls[0] == ("existing-session", "test-agent")


def test_initialize_bidi_agent_skips_read_agent_for_new_session(mock_repository):
    """Test that initialize_bidi_agent() skips read_agent() call when _is_new_session is True."""
    # Create manager (new session)
    manager = RepositorySessionManager(session_id="new-session", session_repository=mock_repository)
    assert manager._is_new_session is True

    # Track read_agent calls
    read_agent_calls = []
    original_read_agent = mock_repository.read_agent

    def tracking_read_agent(session_id, agent_id):
        read_agent_calls.append((session_id, agent_id))
        return original_read_agent(session_id, agent_id)

    mock_repository.read_agent = tracking_read_agent

    # Create mock BidiAgent
    bidi_agent = Mock()
    bidi_agent.agent_id = "bidi-agent-1"
    bidi_agent.messages = [{"role": "user", "content": [{"text": "Hello!"}]}]
    bidi_agent.state = AgentState({})

    # Initialize bidi agent
    manager.initialize_bidi_agent(bidi_agent)

    # read_agent should NOT be called for new session
    assert len(read_agent_calls) == 0


def test_initialize_bidi_agent_calls_read_agent_for_existing_session(mock_repository):
    """Test that initialize_bidi_agent() calls read_agent() when _is_new_session is False."""
    # Create session first
    session = Session(session_id="existing-session", session_type=SessionType.AGENT)
    mock_repository.create_session(session)

    # Create manager (existing session)
    manager = RepositorySessionManager(session_id="existing-session", session_repository=mock_repository)
    assert manager._is_new_session is False

    # Track read_agent calls
    read_agent_calls = []
    original_read_agent = mock_repository.read_agent

    def tracking_read_agent(session_id, agent_id):
        read_agent_calls.append((session_id, agent_id))
        return original_read_agent(session_id, agent_id)

    mock_repository.read_agent = tracking_read_agent

    # Create mock BidiAgent
    bidi_agent = Mock()
    bidi_agent.agent_id = "bidi-agent-1"
    bidi_agent.messages = [{"role": "user", "content": [{"text": "Hello!"}]}]
    bidi_agent.state = AgentState({})

    # Initialize bidi agent
    manager.initialize_bidi_agent(bidi_agent)

    # read_agent should be called for existing session
    assert len(read_agent_calls) == 1
    assert read_agent_calls[0] == ("existing-session", "bidi-agent-1")


def test_initialize_multi_agent_skips_read_for_new_session(mock_repository):
    """Test that initialize_multi_agent() skips read_multi_agent() call when _is_new_session is True."""
    # Create manager (new session)
    manager = RepositorySessionManager(session_id="new-session", session_repository=mock_repository)
    assert manager._is_new_session is True

    # Track read_multi_agent calls
    read_multi_agent_calls = []
    original_read_multi_agent = mock_repository.read_multi_agent

    def tracking_read_multi_agent(session_id, multi_agent_id, **kwargs):
        read_multi_agent_calls.append((session_id, multi_agent_id))
        return original_read_multi_agent(session_id, multi_agent_id, **kwargs)

    mock_repository.read_multi_agent = tracking_read_multi_agent

    # Create mock multi-agent
    multi_agent = Mock()
    multi_agent.id = "test-multi-agent"
    multi_agent.serialize_state.return_value = {"id": "test-multi-agent", "state": {}}

    # Initialize multi-agent
    manager.initialize_multi_agent(multi_agent)

    # read_multi_agent should NOT be called for new session
    assert len(read_multi_agent_calls) == 0


def test_initialize_multi_agent_calls_read_for_existing_session(mock_repository):
    """Test that initialize_multi_agent() calls read_multi_agent() when _is_new_session is False."""
    # Create session first
    session = Session(session_id="existing-session", session_type=SessionType.AGENT)
    mock_repository.create_session(session)

    # Create manager (existing session)
    manager = RepositorySessionManager(session_id="existing-session", session_repository=mock_repository)
    assert manager._is_new_session is False

    # Track read_multi_agent calls
    read_multi_agent_calls = []
    original_read_multi_agent = mock_repository.read_multi_agent

    def tracking_read_multi_agent(session_id, multi_agent_id, **kwargs):
        read_multi_agent_calls.append((session_id, multi_agent_id))
        return original_read_multi_agent(session_id, multi_agent_id, **kwargs)

    mock_repository.read_multi_agent = tracking_read_multi_agent

    # Create mock multi-agent
    multi_agent = Mock()
    multi_agent.id = "test-multi-agent"
    multi_agent.serialize_state.return_value = {"id": "test-multi-agent", "state": {}}

    # Initialize multi-agent
    manager.initialize_multi_agent(multi_agent)

    # read_multi_agent should be called for existing session
    assert len(read_multi_agent_calls) == 1
    assert read_multi_agent_calls[0] == ("existing-session", "test-multi-agent")
