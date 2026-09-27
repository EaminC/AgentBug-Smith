import pytest
from pydantic import BaseModel
from crewai.lite_agent import LiteAgent
from crewai.llms.base_llm import BaseLLM


def test_lite_agent_with_custom_llm_and_guardrails():
    """Test that CustomLLM (inheriting from BaseLLM) works with guardrails."""

    class CustomLLM(BaseLLM):
        def __init__(self, response: str = "Custom response"):
            super().__init__(model="custom-model")
            self.response = response
            self.call_count = 0

        def call(self, messages, tools=None, callbacks=None, available_functions=None, from_task=None, from_agent=None) -> str:
            self.call_count += 1

            # Simulate guardrail validation response
            if "valid" in str(messages) and "feedback" in str(messages):
                return '{"valid": true, "feedback": null}'

            # Simulate agent reasoning and final answer
            if "Thought:" in str(messages):
                return f"Thought: I will analyze soccer players\nFinal Answer: {self.response}"

            return self.response

        def supports_function_calling(self) -> bool:
            return False

        def supports_stop_words(self) -> bool:
            return False

        def get_context_window_size(self) -> int:
            return 4096

    custom_llm = CustomLLM(response="Brazilian soccer players are the best!")

    agent = LiteAgent(
        role="Sports Analyst",
        goal="Analyze soccer players",
        backstory="You analyze soccer players and their performance.",
        llm=custom_llm,
        guardrail="Only include Brazilian players"
    )

    result = agent.kickoff("Tell me about the best soccer players")

    assert custom_llm.call_count > 0
    assert "Brazilian" in result.raw

    # Test guardrail as callable with CustomLLM
    custom_llm2 = CustomLLM(response="Original response")

    def test_guardrail(output):
        return (True, "Modified by guardrail")

    agent2 = LiteAgent(
        role="Test Agent",
        goal="Test goal",
        backstory="Test backstory",
        llm=custom_llm2,
        guardrail=test_guardrail
    )

    result2 = agent2.kickoff("Test message")
    assert result2.raw == "Modified by guardrail"


@pytest.mark.vcr(filter_headers=["authorization"])
def test_lite_agent_with_invalid_llm():
    """Test that LiteAgent raises proper error when create_llm returns None."""
    import crewai.lite_agent
    from unittest.mock import patch

    with patch('crewai.lite_agent.create_llm', return_value=None):
        with pytest.raises(ValueError) as exc_info:
            LiteAgent(
                role="Test Agent",
                goal="Test goal",
                backstory="Test backstory",
                llm="invalid-model"
            )
        assert "Expected LLM instance of type BaseLLM" in str(exc_info.value)
