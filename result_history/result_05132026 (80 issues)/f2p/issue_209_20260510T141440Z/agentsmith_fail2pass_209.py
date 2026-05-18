import asyncio
import pytest

from dapr_agents.agents.orchestrators.llm.orchestrator import LLMOrchestrator
from dapr_agents.agents.orchestrators.random import RandomOrchestrator
from dapr_agents.agents.orchestrators.roundrobin import RoundRobinOrchestrator


@pytest.mark.asyncio
async def test_llm_orchestrator_final_summary_callback():
    called = {}

    def callback(summary: str) -> None:
        called["summary"] = summary

    # Instantiate LLMOrchestrator with the final_summary_callback
    orchestrator = LLMOrchestrator()
    # Monkeypatch the private callback attribute (simulate patch injection)
    orchestrator._final_summary_callback = callback

    # Run the orchestrator's run method with a dummy prompt that triggers completion
    # We simulate a minimal run that returns a final summary string
    # Because we cannot run a full workflow here, we call the internal method that triggers the callback
    test_summary = "final summary from test"
    orchestrator._invoke_final_summary_callback(test_summary)

    # Assert callback was called with the correct summary
    assert "summary" in called
    assert called["summary"] == test_summary


@pytest.mark.asyncio
async def test_random_orchestrator_final_summary_callback():
    called = {}

    def callback(summary: str) -> None:
        called["summary"] = summary

    orchestrator = RandomOrchestrator()
    orchestrator._final_summary_callback = callback

    # Simulate the callback invocation with a test summary
    test_summary = "random orchestrator final output"
    orchestrator._invoke_final_summary_callback(test_summary)

    assert "summary" in called
    assert called["summary"] == test_summary


@pytest.mark.asyncio
async def test_roundrobin_orchestrator_final_summary_callback():
    called = {}

    def callback(summary: str) -> None:
        called["summary"] = summary

    orchestrator = RoundRobinOrchestrator()
    orchestrator._final_summary_callback = callback

    # Simulate the callback invocation with a test summary
    test_summary = "roundrobin orchestrator final output"
    orchestrator._invoke_final_summary_callback(test_summary)

    assert "summary" in called
    assert called["summary"] == test_summary
