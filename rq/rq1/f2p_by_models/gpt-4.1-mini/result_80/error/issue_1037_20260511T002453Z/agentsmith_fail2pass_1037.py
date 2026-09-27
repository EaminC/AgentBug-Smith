import os
import pytest
import asyncio
from src.agentscope.agent._react_agent import ReActAgent
from src.agentscope.message import Msg
from src.agentscope.formatter.dashscope import DashScopeChatFormatter


class DummyMemory:
    def __init__(self):
        self._messages = []
        self._added = []

    async def get_memory(self):
        # Return stored messages as a list
        return self._messages

    async def add(self, msg):
        # Record added messages for test verification
        self._added.append(msg)
        self._messages.append(msg)


class DummyModel:
    """
    Dummy model that simulates an async callable returning a response
    with structured output in metadata.
    """

    def __init__(self):
        self.call_count = 0

    async def __call__(self, prompt, tools=None, tool_choice=None):
        self.call_count += 1
        # Simulate a response with structured output metadata
        # The ReActAgent expects a Msg-like object or dict with content blocks
        # But model returns a dict-like response; the agent's formatter will handle it.
        # Here we simulate the model returning a dict with 'choices' key.
        return {
            "choices": [
                {
                    "message": Msg(
                        content="Structured output generated",
                        metadata={"structured_output": {"key": "value"}},
                    )
                }
            ]
        }


class DummyModelNoStructured:
    """
    Dummy model that simulates an async callable returning a response
    without structured output metadata.
    """

    def __init__(self):
        self.call_count = 0

    async def __call__(self, prompt, tools=None, tool_choice=None):
        self.call_count += 1
        # Simulate a response with no structured output metadata
        return {
            "choices": [
                {
                    "message": Msg(
                        content="No structured output",
                        metadata=None,
                    )
                }
            ]
        }


@pytest.mark.asyncio
async def test_static_control_records_longterm_memory_with_structured_output():
    """
    Test that under static_control mode, when structured output is generated,
    the agent records the reply message to longterm memory.
    """
    dummy_memory = DummyMemory()

    sys_prompt = "system prompt"
    model = DummyModel()
    formatter = DashScopeChatFormatter()

    agent = ReActAgent(
        name="test_agent",
        sys_prompt=sys_prompt,
        model=model,
        formatter=formatter,
        memory=dummy_memory,
        max_iters=3,
    )
    agent._static_control = True

    # Run the agent reply method without arguments (no msg)
    reply_msg = await agent.reply()

    # The reply message should have metadata with structured_output
    assert reply_msg.metadata is not None
    assert "structured_output" in reply_msg.metadata

    # The dummy memory should have recorded the reply message once
    assert len(dummy_memory._added) == 1
    # The recorded message should be the same as reply_msg
    assert dummy_memory._added[0] == reply_msg


@pytest.mark.asyncio
async def test_static_control_no_duplicate_memory_add_when_no_structured_output():
    """
    Test that under static_control mode, if no structured output is generated,
    the agent still returns a reply and records it once.

    This test ensures no duplicate or missing memory additions.
    """
    dummy_memory = DummyMemory()

    sys_prompt = "system prompt"
    model = DummyModelNoStructured()
    formatter = DashScopeChatFormatter()

    agent = ReActAgent(
        name="test_agent",
        sys_prompt=sys_prompt,
        model=model,
        formatter=formatter,
        memory=dummy_memory,
        max_iters=1,
    )
    agent._static_control = True

    # Run the agent reply method without arguments (no msg)
    reply_msg = await agent.reply()

    # The reply message should have no structured output metadata
    assert reply_msg.metadata is None or "structured_output" not in reply_msg.metadata

    # The dummy memory should have recorded the reply message once
    assert len(dummy_memory._added) == 1
    # The recorded message should be the same as reply_msg
    assert dummy_memory._added[0] == reply_msg