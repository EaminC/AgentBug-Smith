```python
# reproducer.py

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


import asyncio
import sys
from typing import AsyncGenerator, Optional
from strands import Agent
from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import MessageStartEvent, MessageStopEvent, MetadataEvent, StreamEvent
from strands.types.tools import ToolChoice, ToolSpec


class MinimalModel(Model):
    async def stream(self, messages: Messages, tool_specs: Optional[list[ToolSpec]] = None,
                     system_prompt: Optional[str] = None, *, tool_choice: ToolChoice | None = None,
                     **kwargs) -> AsyncGenerator[StreamEvent, None]:
        yield StreamEvent(messageStart=MessageStartEvent(role="assistant"))
        yield StreamEvent(contentBlockStart={"contentBlockIndex": 0, "start": {}})
        yield StreamEvent(contentBlockDelta={"delta": {"text": "Hi"}, "contentBlockIndex": 0})
        yield StreamEvent(contentBlockStop={"contentBlockIndex": 0})
        yield StreamEvent(messageStop=MessageStopEvent(stopReason="end_turn"))
        # MetadataEvent has total=False, so metrics should be optional, but this raises KeyError:
        yield StreamEvent(metadata=MetadataEvent(usage={"inputTokens": 5, "outputTokens": 2, "totalTokens": 7}))

    async def structured_output(self, *args, **kwargs):
        raise NotImplementedError()

    def get_config(self) -> dict:
        return {}

    def update_config(self, **kwargs) -> None:
        pass


async def main():
    try:
        await Agent(model=MinimalModel()).invoke_async("test")
    except KeyError as e:
        if e.args and e.args[0] == "metrics":
            print_stacktrace(e)
            # Issue reproduced, exit with non-zero to signal failure
            raise AssertionError("KeyError 'metrics' raised, indicating the issue is present.") from e
        else:
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError:
        sys.exit(1)
    # If no error, exit with 0 indicating the issue is fixed
    sys.exit(0)
```
