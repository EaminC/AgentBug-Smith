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

from agentscope.message import TextBlock, ThinkingBlock
from agentscope.model import ChatResponse
from agentscope.agent import Agent

class _Stub:
    class state:
        reply_id = "r"

convert = Agent._convert_chat_response_to_event.__get__(_Stub())

# A well-behaved reasoning stream: reasoning fully precedes the answer,
# delivered in SEPARATE chunks (how DeepSeek / Qwen reasoning models stream).
chunks = [
    ChatResponse(content=[ThinkingBlock(thinking="reason")], is_last=False),
    ChatResponse(content=[TextBlock(text="Hello")], is_last=False),  # boundary: reasoning done, answer begins
]

async def main():
    block_ids = {"text": None, "thinking": None, "tools": []}
    seq = []
    for ch in chunks:
        async for ev in convert(block_ids, ch):
            seq.append(type(ev).__name__)
    # Expected output order at reasoning->answer boundary:
    expected = [
        "ThinkingBlockStartEvent",
        "ThinkingBlockDeltaEvent",
        "ThinkingBlockEndEvent",
        "TextBlockStartEvent",
        "TextBlockDeltaEvent",
    ]
    # Actually got seq:
    # ThinkingBlockEndEvent should appear before the first TextBlockDeltaEvent
    # Otherwise first answer token trapped inside <think> block.

    # Let's check order by index positions:
    try:
        idx_think_end = seq.index("ThinkingBlockEndEvent")
        idx_text_delta = seq.index("TextBlockDeltaEvent")
        # Assert thinking end BEFORE text delta
        assert idx_think_end < idx_text_delta, (
            f"ThinkingBlockEndEvent occurs at position {idx_think_end}, "
            f"but TextBlockDeltaEvent occurs earlier at position {idx_text_delta} - out of order"
        )
    except Exception as e:
        print_stacktrace(e)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError:
        # Presence of assertion failure means the bug is present -> exit 1
        sys.exit(1)
    # No assertion failure means bug fixed -> exit 0
    sys.exit(0)
```
