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


import sys
import asyncio
import json

from tests.utils import MockModel

from agentscope.agent import Agent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.message import (
    AssistantMsg,
    TextBlock,
    ToolCallBlock,
    ToolResultBlock,
    ToolResultState,
    UserMsg,
)
from agentscope.state import AgentState
from agentscope.tool import Toolkit


async def main():
    agent = Agent(
        name="Friday",
        system_prompt="",
        model=MockModel(context_size=1000),
        toolkit=Toolkit(),
        state=AgentState(
            session_id="multi-tool-compression",
            context=[
                UserMsg("User", "old" * 80),
                AssistantMsg(
                    "Friday",
                    [
                        ToolCallBlock(
                            id="tc1",
                            name="first_tool",
                            input=json.dumps({"value": "a" * 80}),
                        ),
                        ToolCallBlock(
                            id="tc2",
                            name="second_tool",
                            input=json.dumps({"value": "b" * 80}),
                        ),
                        ToolResultBlock(
                            id="tc1",
                            name="first_tool",
                            output=[TextBlock(text="first result " * 8)],
                            state=ToolResultState.SUCCESS,
                        ),
                        ToolResultBlock(
                            id="tc2",
                            name="second_tool",
                            output=[TextBlock(text="second result " * 8)],
                            state=ToolResultState.SUCCESS,
                        ),
                        TextBlock(text="Both tools completed."),
                    ],
                ),
                UserMsg("User", "latest question"),
            ],
        ),
    )

    to_compress, to_reserve = (
        await agent._split_context_for_compression(
            to_reserved_tokens=86,
            tools=[],
        )
    )

    # We expect the reserved context to start with a tool_result matching the last tool_call in reserved.
    # If the bug is present, the first reserved block is an unmatched tool_result.

    # Collect first blocks of each AssistantMsg in reserved:
    reserved_first_blocks = []
    for msg in to_reserve:
        content = msg.get_content_blocks()
        if not content:
            continue
        reserved_first_blocks.append((content[0].type, content[0].id))

    # In particular, check if there is any orphan tool_result separated from its matching tool_call.
    # The repro shows that the first block in reserved is a tool_result block for tc2 but call2 is compressed side.

    # Also check for unmatched tool_result in reserved:
    try:
        # We expect: reserved must not start with tool_result missing matching tool_call in reserved
        # Here we conservatively assert no "tool_result" appears before the matching "tool_call" in reserved

        # Gather tool_call ids in reserved
        reserved_tool_call_ids = set()
        for msg in to_reserve:
            for block in msg.get_content_blocks():
                if block.type == "tool_call":
                    reserved_tool_call_ids.add(block.id)

        # Check tool_result blocks in reserved
        for msg in to_reserve:
            for block in msg.get_content_blocks():
                if block.type == "tool_result":
                    # If the tool_result id is not in reserved_tool_call_ids,
                    # we have an orphan tool_result in reserved (the bug)
                    if block.id not in reserved_tool_call_ids:
                        raise AssertionError(
                            f"Orphan tool_result with id={block.id} in reserved context without matching tool_call."
                        )
    except AssertionError as e:
        print_stacktrace(e)
        raise

    # If no assertion error, exit with 0
    print("No orphan tool_result found in reserved context, compression is correct.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError:
        sys.exit(1)
    sys.exit(0)
```
