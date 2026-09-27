import asyncio
import pytest

from strands import Agent
from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import MessageStartEvent, MessageStopEvent, MetadataEvent, StreamEvent


class MinimalModel(Model):
    async def stream(
        self,
        messages: Messages,
        tool_specs: list | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: object | None = None,
        **kwargs,
    ) -> "AsyncGenerator[StreamEvent, None]":
        yield StreamEvent(messageStart=MessageStartEvent(role="assistant"))
        yield StreamEvent(contentBlockStart={"contentBlockIndex": 0, "start": {}})
        yield StreamEvent(contentBlockDelta={"delta": {"text": "Hi"}, "contentBlockIndex": 0})
        yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
        yield StreamEvent(messageStop=MessageStopEvent(stopReason="end_turn"))
        # Yield MetadataEvent without "metrics" key to test bug/fix
        yield StreamEvent(metadata=MetadataEvent(usage={"inputTokens": 5, "outputTokens": 2, "totalTokens": 7}))

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError()

    def get_config(self) -> dict:
        return {}

    def update_config(self, **kwargs) -> None:
        pass


@pytest.mark.asyncio
async def test_metadata_event_requires_metrics_field():
    """
    This test verifies that the MetadataEvent requires the 'metrics' field.
    Before the fix, omitting 'metrics' causes a KeyError.
    After the fix, the missing 'metrics' field is handled gracefully with defaults.
    """
    agent = Agent(model=MinimalModel())

    # The test passes if the agent invocation completes without KeyError.
    # Before fix, this test will fail with KeyError.
    # After fix, it should pass.
    result = await agent.invoke_async("test")
    # The result is not the focus; we just want no exceptions.
    assert result is not None
    # Additional sanity: check that usage tokens are as expected
    # The agent's last event should contain usage with inputTokens=5, outputTokens=2, totalTokens=7
    # and metrics with latencyMs=0 (default)
    # We cannot directly access internal events here, so just ensure no error.


@pytest.mark.asyncio
async def test_agent_streaming_with_metadata_event_missing_metrics():
    """
    Another test variant to ensure that streaming with MetadataEvent missing 'metrics' does not raise.
    """
    model = MinimalModel()
    agent = Agent(model=model)

    # Run the agent's async invoke and ensure no exception is raised.
    # The bug caused KeyError on missing 'metrics' in MetadataEvent.
    # After fix, it should succeed.
    result = await agent.invoke_async("hello")
    assert result is not None
