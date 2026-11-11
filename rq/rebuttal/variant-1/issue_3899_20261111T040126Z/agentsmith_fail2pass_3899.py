import pytest

from crewai.a2a.config import A2AConfig


@pytest.mark.parametrize(
    "trust_remote_completion_status, a2a_status, expect_direct_return",
    [
        (True, "completed", True),
        (True, "input_required", False),
        (False, "completed", False),
        (False, "input_required", False),
    ],
)
def test_a2a_delegate_trust_remote_completion_status_behavior(
    trust_remote_completion_status, a2a_status, expect_direct_return
):
    """
    Test that when trust_remote_completion_status=True and A2A returns status "completed",
    the _delegate_to_a2a returns the remote result directly without delegating again.

    When trust_remote_completion_status=False or status != "completed",
    the server agent handles the response and may delegate again.
    """
    try:
        from crewai.a2a.wrapper import _delegate_to_a2a
        from crewai import Agent, Task
    except ImportError:
        pytest.skip("crewai.a2a.wrapper or crewai not installed")

    # Setup agent with A2AConfig
    a2a_config = A2AConfig(
        endpoint="http://dummy-endpoint/",
        trust_remote_completion_status=trust_remote_completion_status,
    )
    agent = Agent(
        role="test role",
        goal="test goal",
        backstory="test backstory",
        a2a=a2a_config,
    )
    task = Task(description="test task", expected_output="test output", agent=agent)

    class DummyAgentResponse:
        is_a2a = True
        message = "dummy message"
        a2a_ids = [a2a_config.endpoint]

    dummy_response = DummyAgentResponse()

    # Mock agent_cards with dummy agent card
    dummy_agent_card = type("AgentCard", (), {"name": "dummy_agent"})()
    agent_cards = {a2a_config.endpoint: dummy_agent_card}

    # Count calls to original_fn to detect delegation
    call_count = 0

    def original_fn(self, task, context, tools):
        nonlocal call_count
        call_count += 1
        return "server agent final answer"

    # Patch execute_a2a_delegation to simulate remote A2A response
    import builtins
    import sys

    # We patch execute_a2a_delegation and _fetch_agent_cards_concurrently inside crewai.a2a.wrapper
    # but without unittest.mock, we do manual patching by monkeypatching sys.modules attributes

    import importlib

    wrapper_mod = importlib.import_module("crewai.a2a.wrapper")

    # Save original functions
    original_execute_a2a_delegation = getattr(wrapper_mod, "execute_a2a_delegation", None)
    original_fetch_agent_cards = getattr(wrapper_mod, "_fetch_agent_cards_concurrently", None)

    def fake_execute_a2a_delegation(*args, **kwargs):
        return {
            "status": a2a_status,
            "result": "remote result",
            "history": [],
        }

    def fake_fetch_agent_cards_concurrently(*args, **kwargs):
        return (agent_cards, {})

    # Monkeypatch
    setattr(wrapper_mod, "execute_a2a_delegation", fake_execute_a2a_delegation)
    setattr(wrapper_mod, "_fetch_agent_cards_concurrently", fake_fetch_agent_cards_concurrently)

    try:
        result = _delegate_to_a2a(
            self=agent,
            agent_response=dummy_response,
            task=task,
            original_fn=original_fn,
            context=None,
            tools=None,
            agent_cards=agent_cards,
            original_task_description="test task",
        )
    finally:
        # Restore original functions
        if original_execute_a2a_delegation is not None:
            setattr(wrapper_mod, "execute_a2a_delegation", original_execute_a2a_delegation)
        if original_fetch_agent_cards is not None:
            setattr(wrapper_mod, "_fetch_agent_cards_concurrently", original_fetch_agent_cards)

    if expect_direct_return:
        # Should return remote result directly and not call original_fn
        assert result == "remote result"
        assert call_count == 0
    else:
        # Should delegate to original_fn (server agent)
        assert result == "server agent final answer"
        assert call_count >= 1


def test_a2a_config_default_trust_remote_completion_status_false():
    """Verify that the default value of trust_remote_completion_status is False."""
    config = A2AConfig(endpoint="http://dummy-endpoint/")
    assert hasattr(config, "trust_remote_completion_status")
    assert config.trust_remote_completion_status is False
