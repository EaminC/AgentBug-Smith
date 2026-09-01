```python
#!/usr/bin/env python3
# reproducer.py
import asyncio
from datetime import timedelta
from strands.tools.mcp import MCPClient
from mcp.client.stdio import stdio_client, StdioServerParameters
import sys

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

SERVER_CODE = '''#!/usr/bin/env python3
# test_server.py
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("test-server")

@mcp.tool()
async def slow_tool() -> str:
    """A tool that takes 3 seconds"""
    await asyncio.sleep(3)
    return "completed"

if __name__ == "__main__":
    mcp.run()
'''

async def main():
    # Write server code to a temporary file
    server_path = "/tmp/test_server.py"
    with open(server_path, "w") as f:
        f.write(SERVER_CODE)

    # Start MCP client connected to this server using stdio transport
    client = MCPClient(
        lambda: stdio_client(StdioServerParameters(
            command="uv",
            args=["run", "--script", server_path]
        ))
    )

    with client:
        issue_triggered = False
        for i in range(5):
            print(f"\n{'='*20} Attempt {i+1} {'='*20}")
            try:
                # Each call sets a 1 second read timeout, but tool sleeps 3 seconds to ensure timeout
                result = await client.call_tool_async(
                    tool_use_id=f"test_{i}",
                    name="slow_tool",
                    arguments={},
                    read_timeout_seconds=timedelta(seconds=1)
                )
                print(f"Success: {result}")
            except Exception as e:
                print(f"Error: {type(e).__name__}: {e}")
                # Check if this is the known symptom of the bug (unknown request ID or ClosedResourceError)
                errname = e.__class__.__name__
                if errname in ("RuntimeError", "anyio.ClosedResourceError"):
                    issue_triggered = True
                    print_stacktrace(e)

        # After all attempts
        if issue_triggered:
            print("\nIssue reproduced: MCPClient connection corrupted after timeout and delayed tool response.", file=sys.stderr)
            raise AssertionError("MCPClient timeout broken connection recreated bug is present")
        else:
            print("\nNo issue detected: MCPClient handles timeout and late responses correctly.", file=sys.stderr)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as e:
        sys.exit(1)
    except Exception as e:
        print_stacktrace(e)
        sys.exit(1)
    sys.exit(0)
```
