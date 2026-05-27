import os
import pytest
import asyncio

from examples.agent.deep_research_agent.deep_research_agent import DeepResearchAgent


@pytest.mark.asyncio
async def test_deep_research_agent_handles_thinking_blocks():
    """
    This test verifies that DeepResearchAgent correctly handles model output blocks
    that start with a 'thinking' block followed by a 'text' block, avoiding KeyError.

    It simulates the buggy scenario where the first block is 'thinking' without 'text' key,
    and expects the agent to extract the 'text' from the correct block.

    On the buggy codebase, this test should fail with KeyError.
    After the fix, it should pass.
    """

    model_name = "Qwen3.5-397B-A17B-FPB"

    # Create the agent instance with environment variable for API key if needed
    agent = DeepResearchAgent(model=model_name)

    thinking_then_text_blocks = [
        {"type": "thinking", "thinking": "processing..."},
        {"type": "text", "text": "This is the final report content."},
    ]

    async def dummy_chat_completions_create(*args, **kwargs):
        return thinking_then_text_blocks

    # Setup dummy model client with chat.completions.create mocked
    class DummyChat:
        def __init__(self):
            self.completions = pytest.AsyncMock()
            self.completions.create = pytest.AsyncMock(side_effect=dummy_chat_completions_create)

    class DummyModel:
        def __init__(self):
            self.chat = DummyChat()
            self.stream = False

    agent.model = DummyModel()

    checklist = "dummy checklist"

    final_report = await agent._generate_deepresearch_report(checklist)

    expected_text = "This is the final report content."

    assert final_report == expected_text, (
        "DeepResearchAgent failed to extract text from blocks with leading thinking block."
    )