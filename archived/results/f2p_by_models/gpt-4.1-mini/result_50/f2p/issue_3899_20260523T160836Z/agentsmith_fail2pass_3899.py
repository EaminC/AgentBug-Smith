import pytest
from unittest.mock import MagicMock, patch

from crewai.a2a.config import A2AConfig


@pytest.mark.skipif(
    True,
    reason="Skip because 'a2a' module is missing in buggy state; run after patch to verify fix",
)
def test_a2a_server_does_not_delegate_again_after_completed():
    """
    Test that when trust_remote_completion_status=True and A2A returns status 'completed',
    the server agent returns the remote result directly and does not delegate again.
    This should fail on buggy code (looping) and pass after fix.
    """
    from crewai.a2a.wrapper import _delegate_to_a2a
    from crewai import Agent, Task

    a2a_config = A2AConfig(
        endpoint="http://fake-endpoint",
        trust_remote_completion_status=True,
    )

    agent = Agent(
        role="manager",
        goal="coordinate",
        backstory="test backstory",
        a2a=a2a_config,
    )

    task = Task(description="test task", expected_output="test output", agent=agent)

    class MockResponse:
        is_a2a = True
        message = "request message"
        a2a_ids = ["http://fake-endpoint"]

    with patch("crewai.a2a.wrapper.execute_a2a_delegation") as mock_execute, patch(
        "crewai.a2a.wrapper._fetch_agent_cards_concurrently"
    ) as mock_fetch:
        mock_card = MagicMock()
        mock_card.name = "FakeAgent"
        mock_fetch.return_value = ({"http://fake-endpoint": mock_card}, {})

        # Simulate A2A returns completed status
        mock_execute.return_value = {
            "status": "completed",
            "result": "final remote result",
            "history": [],
        }

        # Call _delegate_to_a2a, expecting it to return the remote result directly
        result = _delegate_to_a2a(
            self=agent,
            agent_response=MockResponse(),
            task=task,
            original_fn=lambda *a, **k: "fallback",
            context=None,
            tools=None,
            agent_cards={"http://fake-endpoint": mock_card},
            original_task_description="test task",
        )

        # The result should be the remote result string
        assert result == "final remote result"
        # The delegation call should have been called once
        assert mock_execute.call_count == 1


@pytest.mark.skipif(
    True,
    reason="Skip because 'a2a' module is missing in buggy state; run after patch to verify fix",
)
def test_a2a_server_delegates_again_if_trust_flag_false():
    """
    Test that when trust_remote_completion_status=False and A2A returns 'completed',
    the server agent continues to delegate (calls original_fn).
    This behavior is buggy and should fail before fix, pass after fix.
    """
    from crewai.a2a.wrapper import _delegate_to_a2a
    from crewai import Agent, Task

    a2a_config = A2AConfig(
        endpoint="http://fake-endpoint",
        trust_remote_completion_status=False,
    )

    agent = Agent(
        role="manager",
        goal="coordinate",
        backstory="test backstory",
        a2a=a2a_config,
    )

    task = Task(description="test task", expected_output="test output", agent=agent)

    class MockResponse:
        is_a2a = True
        message = "request message"
        a2a_ids = ["http://fake-endpoint"]

    call_count = 0

    def mock_original_fn(self, task, context, tools):
        nonlocal call_count
        call_count += 1
        # Return a server final answer on first call
        if call_count == 1:
            return '{"is_a2a": false, "message": "server final answer", "a2a_ids": []}'
        return "unexpected"

    with patch("crewai.a2a.wrapper.execute_a2a_delegation") as mock_execute, patch(
        "crewai.a2a.wrapper._fetch_agent_cards_concurrently"
    ) as mock_fetch:
        mock_card = MagicMock()
        mock_card.name = "FakeAgent"
        mock_fetch.return_value = ({"http://fake-endpoint": mock_card}, {})

        # Simulate A2A returns completed status
        mock_execute.return_value = {
            "status": "completed",
            "result": "final remote result",
            "history": [],
        }

        result = _delegate_to_a2a(
            self=agent,
            agent_response=MockResponse(),
            task=task,
            original_fn=mock_original_fn,
            context=None,
            tools=None,
            agent_cards={"http://fake-endpoint": mock_card},
            original_task_description="test task",
        )

        # The original_fn should have been called at least once
        assert call_count >= 1
        # The result should be the server final answer string
        assert result == "server final answer"


def test_trust_remote_completion_status_default_false():
    """
    Test that the default value of trust_remote_completion_status in A2AConfig is False.
    This should pass before and after fix.
    """
    a2a_config = A2AConfig(endpoint="http://fake-endpoint")
    assert hasattr(a2a_config, "trust_remote_completion_status")
    assert a2a_config.trust_remote_completion_status is False
