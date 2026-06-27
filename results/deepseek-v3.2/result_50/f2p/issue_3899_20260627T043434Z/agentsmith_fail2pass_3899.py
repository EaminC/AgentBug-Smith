import pytest
from unittest.mock import MagicMock, patch
from crewai.a2a.config import A2AConfig

try:
    from a2a.types import Role
    A2A_SDK_INSTALLED = True
except ImportError:
    A2A_SDK_INSTALLED = False

@pytest.mark.skipif(not A2A_SDK_INSTALLED, reason="Requires a2a-sdk to be installed")
def test_trust_remote_completion_status_true_returns_directly():
    """When trust_remote_completion_status=True and A2A returns completed, return result directly."""
    from crewai.a2a.wrapper import _delegate_to_a2a
    from crewai import Agent, Task

    a2a_config = A2AConfig(
        endpoint="http://test-endpoint.com",
        trust_remote_completion_status=True,
    )

    agent = Agent(
        role="test manager",
        goal="coordinate",
        backstory="test",
        a2a=a2a_config,
    )

    task = Task(description="test", expected_output="test", agent=agent)

    class MockResponse:
        is_a2a = True
        message = "Please help"
        a2a_ids = ["http://test-endpoint.com/"]

    with (
        patch("crewai.a2a.wrapper.execute_a2a_delegation") as mock_execute,
        patch("crewai.a2a.wrapper._fetch_agent_cards_concurrently") as mock_fetch,
    ):
        mock_card = MagicMock()
        mock_card.name = "Test"
        mock_fetch.return_value = ({"http://test-endpoint.com/": mock_card}, {})

        mock_execute.return_value = {
            "status": "completed",
            "result": "Done by remote",
            "history": [],
        }

        result = _delegate_to_a2a(
            self=agent,
            agent_response=MockResponse(),
            task=task,
            original_fn=lambda *args, **kwargs: "fallback",
            context=None,
            tools=None,
            agent_cards={"http://test-endpoint.com/": mock_card},
            original_task_description="test",
        )

        assert result == "Done by remote"
        assert mock_execute.call_count == 1

@pytest.mark.skipif(not A2A_SDK_INSTALLED, reason="Requires a2a-sdk to be installed")
def test_trust_remote_completion_status_false_causes_loop():
    """When trust_remote_completion_status=False and A2A returns completed, server agent should loop (buggy)."""
    from crewai.a2a.wrapper import _delegate_to_a2a
    from crewai import Agent, Task

    a2a_config = A2AConfig(
        endpoint="http://test-endpoint.com",
        trust_remote_completion_status=False,
    )

    agent = Agent(
        role="test manager",
        goal="coordinate",
        backstory="test",
        a2a=a2a_config,
    )

    task = Task(description="test", expected_output="test", agent=agent)

    class MockResponse:
        is_a2a = True
        message = "Please help"
        a2a_ids = ["http://test-endpoint.com/"]

    call_count = 0
    def mock_original_fn(self, task, context, tools):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '{"is_a2a": false, "message": "Server final answer", "a2a_ids": []}'
        return "unexpected"

    with (
        patch("crewai.a2a.wrapper.execute_a2a_delegation") as mock_execute,
        patch("crewai.a2a.wrapper._fetch_agent_cards_concurrently") as mock_fetch,
        patch("crewai.a2a.wrapper._handle_agent_response_and_continue") as mock_handle,
    ):
        mock_card = MagicMock()
        mock_card.name = "Test"
        mock_fetch.return_value = ({"http://test-endpoint.com/": mock_card}, {})

        mock_execute.return_value = {
            "status": "completed",
            "result": "Done by remote",
            "history": [],
        }

        mock_handle.return_value = (None, "next_request")

        result = _delegate_to_a2a(
            self=agent,
            agent_response=MockResponse(),
            task=task,
            original_fn=mock_original_fn,
            context=None,
            tools=None,
            agent_cards={"http://test-endpoint.com/": mock_card},
            original_task_description="test",
        )

        assert mock_handle.called
        assert result is None

def test_default_trust_remote_completion_status_is_false():
    """Verify that default value of trust_remote_completion_status is False."""
    a2a_config = A2AConfig(
        endpoint="http://test-endpoint.com",
    )
    assert a2a_config.trust_remote_completion_status is False, "Default should be False for backward compatibility"
