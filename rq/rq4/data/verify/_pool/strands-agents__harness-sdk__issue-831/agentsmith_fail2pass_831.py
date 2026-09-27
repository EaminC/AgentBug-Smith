import pytest
from pydantic import BaseModel
from strands import Agent
from strands.models import BedrockModel


@pytest.mark.asyncio
async def test_structured_output_callback_invoked():
    # Setup a BedrockModel with a mocked stream method to simulate structured output streaming events
    model = BedrockModel()

    # We simulate the streaming of structured output events with incremental JSON fragments and metadata
    async def fake_stream(*args, **kwargs):
        yield {
            "contentBlockStart": {
                "start": {"toolUse": {"toolUseId": "tooluse_123", "name": "ContactCard"}},
                "contentBlockIndex": 0,
            }
        }
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": ""}}, "contentBlockIndex": 0}}
        yield {
            "contentBlockDelta": {
                "delta": {
                    "toolUse": {
                        "input": '{"name": "John", "age": 38, "address": "123 anytown usa, Texas, 78756" }'
                    }
                },
                "contentBlockIndex": 0,
            }
        }
        yield {"contentBlockStop": {"contentBlockIndex": 0}}
        yield {"messageStop": {"stopReason": "tool_use"}}
        yield {
            "metadata": {
                "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
                "metrics": {"latencyMs": 100},
            }
        }

    model.stream = fake_stream

    # Collect callback events here
    events = []

    def callback_handler(**kwargs):
        events.append(kwargs)

    agent = Agent(model=model, callback_handler=callback_handler)

    class ContactCard(BaseModel):
        name: str
        age: int
        address: str

    # Call structured_output_async to get structured output and trigger callbacks
    result = await agent.structured_output_async(
        ContactCard,
        "Convert the following data to a contact card <input> John, last name Smith, who resides at 123 anytown usa, Texas, 78756, and is of age 38</input>",
    )

    # We expect the callback_handler to have been called with events during the streaming
    assert len(events) > 0, "Callback handler was not invoked with any events"

    # Check that at least one event contains the expected keys
    found_tool_use_event = any(
        "current_tool_use" in event and event["current_tool_use"].get("name") == "ContactCard"
        for event in events
    )
    assert found_tool_use_event, "Expected tool use event not found in callback events"

    # The structured output result should be an instance of ContactCard or compatible
    assert hasattr(result, "name") and hasattr(result, "age") and hasattr(result, "address")
    assert result.name == "John"
    assert result.age == 38
    assert result.address == "123 anytown usa, Texas, 78756"
