import pytest
from pydantic import BaseModel
from strands.agent import Agent
from strands.hooks import BeforeInvocationEvent
from tests.fixtures.mocked_model_provider import MockedModelProvider


def test_before_invocation_event_messages_are_passed_and_modifiable():
    """
    Test that the BeforeInvocationEvent receives the input messages and that
    hooks can modify the messages in-place to redact sensitive content.
    """

    mock_provider = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [{"text": "I received your redacted message"}],
            },
        ]
    )

    modified_content = None

    async def redact_secret_hook(event: BeforeInvocationEvent):
        nonlocal modified_content
        # The messages should be present in the event
        assert event.messages is not None
        # Redact "SECRET" in user messages
        for message in event.messages:
            if message.get("role") == "user":
                content = message.get("content", [])
                for block in content:
                    if "text" in block and "SECRET" in block["text"]:
                        block["text"] = block["text"].replace("SECRET", "[REDACTED]")
        modified_content = event.messages[0]["content"][0]["text"]

    agent = Agent(model=mock_provider)
    agent.hooks.add_callback(BeforeInvocationEvent, redact_secret_hook)

    # Invoke the agent with a message containing sensitive content
    result = agent("My password is SECRET123")

    # Verify the message was modified before being processed
    assert modified_content == "My password is [REDACTED]123"
    # Verify the modified message was added to agent's conversation history
    assert agent.messages[0]["content"][0]["text"] == "My password is [REDACTED]123"


def test_before_invocation_event_messages_can_be_replaced():
    """
    Test that the BeforeInvocationEvent allows replacing the entire messages list,
    and that the agent processes the replaced messages.
    """

    mock_provider = MockedModelProvider(
        [
            {
                "role": "assistant",
                "content": [{"text": "Received the overwritten message"}],
            },
        ]
    )

    async def overwrite_messages_hook(event: BeforeInvocationEvent):
        # Replace the messages with a new list
        event.messages = [{"role": "user", "content": [{"text": "OVERWRITTEN"}]}]

    agent = Agent(model=mock_provider)
    agent.hooks.add_callback(BeforeInvocationEvent, overwrite_messages_hook)

    # Call agent with arbitrary input; hook replaces it
    result = agent("Original message")

    # Verify the message was overwritten to agent's conversation history
    assert agent.messages[0]["content"][0]["text"] == "OVERWRITTEN"


@pytest.mark.asyncio
async def test_before_invocation_event_messages_none_in_structured_output(agenerator):
    """
    Test that BeforeInvocationEvent.messages is None when called from structured_output_async,
    which does not pass messages.
    """

    class Person(BaseModel):
        name: str
        age: int

    mock_provider = MockedModelProvider([])
    from unittest.mock import Mock

    mock_provider.structured_output = Mock(return_value=agenerator([{"output": Person(name="Test", age=30)}]))

    received_messages = "not_set"

    async def capture_messages_hook(event: BeforeInvocationEvent):
        nonlocal received_messages
        received_messages = event.messages

    agent = Agent(model=mock_provider)
    agent.hooks.add_callback(BeforeInvocationEvent, capture_messages_hook)

    await agent.structured_output_async(Person, "Test prompt")

    # structured_output_async uses deprecated path that doesn't pass messages
    assert received_messages is None
