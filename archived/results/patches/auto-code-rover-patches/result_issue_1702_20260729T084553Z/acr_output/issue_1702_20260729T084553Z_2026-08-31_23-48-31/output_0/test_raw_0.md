```python
# reproducer.py
import asyncio
import json
import sys

from agentscope.message import ToolCallBlock
from agentscope.state import AgentState
from agentscope.tool import FunctionTool, Toolkit


def print_stacktrace(e: Exception):
    import traceback
    tb = traceback.extract_tb(e.__traceback__)
    print("Traceback (most recent call last):", file=sys.stderr)
    for frame in tb:
        line_number = frame.lineno
        code_context = frame.line.strip() if frame.line else "Unknown"
        print(f'  File "{frame.filename}"', file=sys.stderr)
        print(f"    {line_number}: {code_context}", file=sys.stderr)
    print(f"{e.__class__.__name__}: {e}", file=sys.stderr)


def get_weather(location: str) -> str:
    """Get weather information.

    Args:
        location (`str`):
            The location to get weather for.
    """
    return f"The weather in {location} is sunny."


async def main() -> None:
    toolkit = Toolkit(tools=[FunctionTool(get_weather)])

    tool_call = ToolCallBlock(
        id="call_get_weather",
        name="get_weather",
        input=json.dumps({"location": "Chengdu"}),
    )

    try:
        async for item in toolkit.call_tool(tool_call, AgentState()):
            # Should produce some ToolChunk or compatible output, not error.
            pass
    except Exception as e:
        # If the error about return type is present, print stacktrace and raise AssertionError
        if "The tool function must return a ToolChunk object" in str(e):
            print_stacktrace(e)
            raise AssertionError(
                "FunctionTool does not accept plain str return, reproducing the reported issue."
            ) from e
        else:
            # Unexpected exception, just re-raise
            raise


if __name__ == "__main__":
    asyncio.run(main())
```
