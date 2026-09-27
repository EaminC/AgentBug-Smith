```python
# reproducer.py
from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk, ToolResponse


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


def main():
    response = ToolResponse()
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="failed")],
            state=ToolResultState.ERROR,
        ),
    )
    response.append_chunk(
        ToolChunk(
            content=[TextBlock(text="interrupted")],
            state=ToolResultState.INTERRUPTED,
        ),
    )

    try:
        assert response.state == ToolResultState.ERROR
    except AssertionError as e:
        print_stacktrace(e)
        raise


if __name__ == "__main__":
    import sys
    try:
        main()
    except AssertionError:
        # The issue is present - propagate the exception with stack trace printed.
        sys.exit(1)
    # Issue fixed - exit with 0
    sys.exit(0)
```