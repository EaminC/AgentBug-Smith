import asyncio
import time
import pytest
from strands.models.bedrock import BedrockModel


@pytest.mark.asyncio
async def test_stream_cancellation_consumes_orphaned_task_exception():
    """Orphaned background task exception is consumed when stream generator is cancelled."""

    # Create a BedrockModel instance with default config
    model = BedrockModel()

    # Define a slow converse_stream side effect that sleeps and then raises
    def slow_converse_stream(**kwargs):
        time.sleep(0.1)
        raise RuntimeError("simulated boto3 timeout")

    # Patch the model's client converse_stream method to the slow side effect
    model.client.converse_stream = slow_converse_stream

    loop = asyncio.get_running_loop()
    captured = []
    # Set a custom exception handler to capture unhandled exceptions
    loop.set_exception_handler(lambda _loop, ctx: captured.append(ctx))

    gen = model.stream([{"role": "user", "content": [{"text": "test"}]}])
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(gen.__anext__(), timeout=0.01)

    # Close the async generator properly to trigger cleanup
    await gen.aclose()

    # Allow the background thread to finish and the done-callback to fire
    await asyncio.sleep(0.2)

    # Assert no unhandled exceptions were captured (no orphaned task exception)
    assert not captured, f"orphaned task exception was not consumed: {captured}"
