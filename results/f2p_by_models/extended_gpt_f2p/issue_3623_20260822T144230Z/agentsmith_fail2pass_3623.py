import asyncio
import pytest
import strands
from strands import Agent
from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, responses, usages=None):
        self._responses = responses
        self._usages = usages or [None] * len(responses)
        self._index = 0

    def format_request(self, messages, tool_specs=None, system_prompt=None):
        return None

    def format_chunk(self, event):
        return event

    def get_config(self):
        return {}

    def update_config(self, **kwargs):
        pass

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        return
        yield

    async def stream(self, messages, tool_specs=None, system_prompt=None, tool_choice=None, **kwargs):
        text = self._responses[self._index]
        usage = None
        if self._usages and self._index < len(self._usages):
            usage = self._usages[self._index]
        self._index += 1
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        if usage is not None:
            yield {"metadata": {"usage": usage, "metrics": {"latencyMs": 0}}}
        else:
            yield {"metadata": {"metrics": {"latencyMs": 0}}}


@pytest.mark.asyncio
async def test_retry_usage_accumulation():
    """
    Test that when AfterModelCallEvent.retry is set, the usage of the discarded call is still accumulated.

    This test reproduces the bug described in issue #3623:
    When a hook retries a model call after a short response, the usage of the first call is dropped.
    After the fix, the usage of both calls should be accumulated.
    """

    # Prepare scripted responses with different usage
    responses = [
        "Short",
        "This is a much longer and more detailed response",
    ]
    usages = [
        {"inputTokens": 1000, "outputTokens": 1000, "totalTokens": 2000},
        {"inputTokens": 7, "outputTokens": 7, "totalTokens": 14},
    ]

    model = ScriptedModel(responses, usages)

    class MinLengthRetryHook:
        def __init__(self, min_length=10):
            self.min_length = min_length
            self.call_count = 0

        def register_hooks(self, registry):
            registry.add_callback(strands.hooks.AfterModelCallEvent, self.handle_after_model_call)

        async def handle_after_model_call(self, event):
            self.call_count += 1
            if event.stop_response:
                message = event.stop_response.message
                text_content = "".join(block.get("text", "") for block in message.get("content", []))
                if len(text_content) < self.min_length:
                    event.retry = True

    retry_hook = MinLengthRetryHook(min_length=10)
    agent = Agent(model=model, hooks=[retry_hook])

    result = agent("Generate a response")

    # The hook should have been called twice: once for the short response, once for the longer response
    assert retry_hook.call_count == 2

    # The final result should be the longer response
    assert result.message["content"][0]["text"] == "This is a much longer and more detailed response"

    # The accumulated usage should include both calls (inputTokens and outputTokens summed)
    # The first call usage: 1000 input + 1000 output = 2000 total tokens
    # The second call usage: 7 input + 7 output = 14 total tokens
    # Total expected: 1007 inputTokens, 1007 outputTokens, 2014 totalTokens
    usage = agent.event_loop_metrics.accumulated_usage
    expected_usage = {"inputTokens": 1007, "outputTokens": 1007, "totalTokens": 2014}
    assert usage == expected_usage, f"Expected usage {expected_usage}, got {usage}"
