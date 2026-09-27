```python
# reproducer.py
import os
import sys
import asyncio
import json
from agentscope.workspace._local_workspace import LocalWorkspace


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


async def main():
    # Setup a temporary workspace directory
    workdir = "./reproducer_workdir"
    os.makedirs(workdir, exist_ok=True)

    # Write the invalid .mcp config file (with is_stateful: false for STDIO MCP)
    mcp_path = os.path.join(workdir, ".mcp")
    invalid_mcp = [
        {
            "name": "bad_mcp",
            "is_stateful": False,
            "mcp_config": {
                "type": "stdio_mcp",
                "command": "echo",
                "args": ["hello"]
            }
        }
    ]
    with open(mcp_path, "w", encoding="utf-8") as f:
        json.dump(invalid_mcp, f, indent=2)

    # Try to initialize the workspace and catch the expected crash
    ws = LocalWorkspace(workdir=workdir)
    try:
        await ws.initialize()
    except Exception as e:
        # The bug manifests as a ValueError complaining about is_stateful=False
        # We assert that is the case, else fail the test
        print_stacktrace(e)
        msg = str(e)
        if "STDIO MCP must be stateful" in msg:
            raise AssertionError(
                "Bug reproducer: ValueError on invalid MCP config crashes workspace"
            ) from e
        else:
            # Unknown error, re-raise
            raise
    else:
        # If no exception, bug is fixed
        print("No error on invalid MCP config. Bug appears fixed.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
```
