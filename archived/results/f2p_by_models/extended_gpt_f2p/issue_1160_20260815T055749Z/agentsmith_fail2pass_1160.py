from unittest.mock import patch, Mock
import pytest

from strands.agent.conversation_manager.summarizing_conversation_manager import SummarizingConversationManager
from strands.types.content import Messages
from strands.agent.agent import Agent


class MockAgent:
    """Mock agent for testing summarization.

    This mock supports _default_structured_output_model attribute and __call__ method.
    """

    def __init__(self, summary_response="This is a summary of the conversation."):
        self.summary_response = summary_response
        self.system_prompt = None
        self.messages = []
        self.model = Mock()
        self.model.stream = Mock()
        self.call_tracker = Mock()
        self.tool_registry = Mock()
        self.tool_names = []
        self._default_structured_output_model = None

    def __call__(self, prompt):
        """Mock agent call that returns a summary."""
        self.call_tracker(prompt)
        result = Mock()
        result.message = {"role": "assistant", "content": [{"text": self.summary_response}]}
        return result


def create_mock_agent(summary_response="This is a summary of the conversation.") -> Agent:
    """Factory function that returns a properly typed MockAgent."""
    return MockAgent(summary_response)


def test_generate_summary_disables_structured_output_on_summarization_agent():
    """Test that structured output is disabled during summarization to avoid toolUse in user messages.

    When a summarization agent has structured_output_model configured, the response contains toolUse blocks.
    Since the summary is converted to a user message, toolUse blocks would violate the model API constraint
    that user messages cannot contain tool uses. The fix disables structured output during summarization.
    """
    summary_agent = create_mock_agent()
    structured_output_model = Mock()
    summary_agent._default_structured_output_model = structured_output_model

    original_call = summary_agent.__class__.__call__
    observed_values = []

    def tracking_call(self, prompt):
        observed_values.append(self._default_structured_output_model)
        return original_call(self, prompt)

    messages: Messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there"}]},
    ]

    manager = SummarizingConversationManager(summarization_agent=summary_agent)

    with patch.object(MockAgent, "__call__", tracking_call):
        manager._generate_summary(messages, create_mock_agent())

    assert observed_values == [None], "structured output should be disabled during summarization"
    assert summary_agent._default_structured_output_model is structured_output_model, "should be restored after"


def test_dedicated_summarization_agent_with_structured_output(model=None, summarization_model=None):
    """Test that summarization works when the summarization agent has structured_output_model configured.

    When structured_output_model is set on the summarization agent, the response would contain toolUse
    blocks. Since the summary is converted to a user message, those blocks would cause a
    ValidationException. This test verifies that structured output is properly disabled during
    summarization.
    """
    # Import pydantic only if available
    from pydantic import BaseModel

    # If model fixtures are not provided, skip this test (integration style)
    if model is None or summarization_model is None:
        pytest.skip("Requires model and summarization_model fixtures")

    class SummaryOutput(BaseModel):
        topics: list[str]
        key_points: list[str]

    # Create a summarization agent with structured_output_model configured
    summarization_agent = Agent(
        model=summarization_model,
        system_prompt="You are a conversation summarizer. Create concise, structured summaries.",
        structured_output_model=SummaryOutput,
        load_tools_from_directory=False,
    )

    agent = Agent(
        model=model,
        conversation_manager=SummarizingConversationManager(
            summary_ratio=0.5,
            preserve_recent_messages=2,
            summarization_agent=summarization_agent,
        ),
        load_tools_from_directory=False,
    )

    # Build conversation history
    agent.messages.extend(
        [
            {"role": "user", "content": [{"text": "Tell me about Python programming."}]},
            {"role": "assistant", "content": [{"text": "Python is a high-level programming language."}]},
            {"role": "user", "content": [{"text": "What about its type system?"}]},
            {"role": "assistant", "content": [{"text": "Python uses dynamic typing with optional type hints."}]},
            {"role": "user", "content": [{"text": "How does async work in Python?"}]},
            {"role": "assistant", "content": [{"text": "Python uses asyncio with async/await syntax."}]},
            {"role": "user", "content": [{"text": "What about decorators?"}]},
            {"role": "assistant", "content": [{"text": "Decorators are functions that modify other functions."}]},
        ]
    )

    original_length = len(agent.messages)
    agent.conversation_manager.reduce_context(agent)

    assert len(agent.messages) < original_length

    summary_message = agent.messages[0]
    assert summary_message["role"] == "user"

    # Summary should contain only valid user message content (no toolUse blocks)
    for content_block in summary_message["content"]:
        assert "toolUse" not in content_block, "Summary user message should not contain toolUse blocks"

    # Should have text content
    assert any("text" in cb for cb in summary_message["content"])

    # Invoke the agent with the summarized messages to verify the provider accepts them
    result = agent("Thanks for the overview!")
    assert result.message["role"] == "assistant"
