```python
# reproducer.py

import asyncio
import strands
from strands import Agent
from strands.models import Model


def print_stacktrace(e: Exception):
    import traceback
    import sys
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


class ScriptedModel(Model):
    def __init__(self, responses):
        self._responses = responses
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
        # yield the scripted answer and usage metadata
        text, usage = self._responses[self._index]
        self._index += 1
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {}}}
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": usage, "metrics": {"latencyMs": 0}}}


async def main():
    model = ScriptedModel(
        [
            ("Short", {"inputTokens": 1000, "outputTokens": 1000, "totalTokens": 2000}),
            ("This is a much longer and more detailed response",
             {"inputTokens": 7, "outputTokens": 7, "totalTokens": 14}),
        ]
    )

    class MinLengthRetryHook:
        def register_hooks(self, registry):
            registry.add_callback(strands.hooks.AfterModelCallEvent, self.handle_after_model_call)

        async def handle_after_model_call(self, event):
            if event.stop_response:
                text = "".join(b.get("text", "") for b in event.stop_response.message.get("content", []))
                if len(text) < 10:
                    event.retry = True

    agent = Agent(model=model, hooks=[MinLengthRetryHook()])

    result = agent("Generate a response")

    # We want the accumulated_usage across all calls including retried calls.
    accumulated = agent.event_loop_metrics.accumulated_usage

    try:
        # The first call has 1000/1000 usage, second has 7/7.
        # The bug: accumulated_usage misses the first call usage entirely.
        # So check that totalTokens >= 2000, otherwise raise to show bug.
        if accumulated.get("totalTokens", 0) < 2000:
            raise AssertionError(
                f"accumulated_usage only shows second call usage, missing retried call. accumulated_usage: {accumulated}"
            )
    except Exception as e:
        print_stacktrace(e)
        raise

    print("Test passed. accumulated_usage includes retried call usage.")


if __name__ == "__main__":
    import sys

    try:
        asyncio.run(main())
    except AssertionError:
        sys.exit(1)
```
