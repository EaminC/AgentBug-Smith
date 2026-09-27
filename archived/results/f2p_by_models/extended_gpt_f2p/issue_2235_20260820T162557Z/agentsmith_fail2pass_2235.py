import pytest
import asyncio

import strands
from strands import Agent
from strands.models.ollama import OllamaModel


class DummyResponseEvent:
    def __init__(self, eval_count, prompt_eval_count, total_duration):
        self.eval_count = eval_count
        self.prompt_eval_count = prompt_eval_count
        self.total_duration = total_duration


class DummyEvent:
    def __init__(self):
        self.chunk_type = "metadata"
        self.data = DummyResponseEvent(eval_count=10, prompt_eval_count=5, total_duration=12345000)


class DummyOllamaModel(OllamaModel):
    async def stream(self, messages, **kwargs):
        # Yield events simulating the stream generator
        # We yield a metadata event with total_duration that should be converted to int latencyMs
        yield {
            "metadata": {
                "usage": {
                    "inputTokens": 5,
                    "outputTokens": 10,
                    "totalTokens": 15,
                },
                "metrics": {
                    "latencyMs": self._convert_latency_ms(12345000),
                },
            }
        }

    def _convert_latency_ms(self, total_duration):
        # This mimics the buggy or fixed behavior depending on the code under test
        # The buggy code returns float, fixed returns int
        # We just return the actual code's behavior by calling format_chunk internally
        dummy_event = DummyEvent()
        dummy_event.data.total_duration = total_duration
        chunk = self.format_chunk({"chunk_type": "metadata", "data": dummy_event.data})
        return chunk["metadata"]["metrics"]["latencyMs"]


@pytest.mark.asyncio
async def test_ollama_latency_ms_type():
    """
    Test that the latencyMs metric returned by OllamaModel is an int, not a float.
    This test should fail on the buggy codebase where latencyMs is float,
    and pass after the fix where latencyMs is converted to int.
    """
    # Create a dummy Ollama model instance with dummy host and model_id
    ollama_model = DummyOllamaModel(
        host="http://dummy-host",
        model_id="dummy-model",
    )

    # Create an agent using the dummy Ollama model
    agent = Agent(
        model=ollama_model,
    )

    # Call the agent with a simple prompt to trigger the stream and get metrics
    # We only need to consume the stream and check the latencyMs type
    events = []
    async for event in ollama_model.stream([{"role": "user", "content": "Hello"}]):
        events.append(event)

    # Find the metadata event
    metadata_events = [e for e in events if "metadata" in e]
    assert len(metadata_events) == 1, "Expected exactly one metadata event"

    latency_ms = metadata_events[0]["metadata"]["metrics"]["latencyMs"]

    # Assert that latencyMs is an int (not float)
    assert isinstance(latency_ms, int), f"latencyMs should be int but got {type(latency_ms)}"

    # Assert that latencyMs is the integer conversion of total_duration / 1e6
    expected_latency = int(12345000 / 1e6)
    assert latency_ms == expected_latency, f"latencyMs should be {expected_latency} but got {latency_ms}"
