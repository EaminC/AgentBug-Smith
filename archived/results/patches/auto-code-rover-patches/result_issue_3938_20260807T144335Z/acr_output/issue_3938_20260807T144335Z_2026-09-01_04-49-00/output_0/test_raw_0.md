```python
# reproducer.py
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


def main():
    # We try to reproduce the error shown in the issue description.
    # The problem is that when creating an MCP client instance
    # with SSE transport, an invalid argument 'terminate_on_close' is passed,
    # resulting in a crash (specifically, UnboundLocalError in _get_native_mcp_tools).
    #
    # To reproduce, we attempt to:
    #  - start MCP server (but here we assume server is running or unnecessary for reproduce)
    #  - create an MCP SSE transport client or trigger the _get_native_mcp_tools()
    #
    # Because this is a library internal error, we simulate by calling the method
    # that creates the client with the problematic argument and catch if the error happens.
    #
    # We import necessary classes from crewAI packages
    # The stack trace in the problem comes from:
    #   crewai.agent.core.Agent._get_native_mcp_tools(mcp_config)
    # called from Agent.get_mcp_tools(...)
    #
    # We try to create the minimal call to trigger the issue.
    #
    # If no exception raised, print "No issue detected" and exit 0
    # If the issue is raised, print the stack trace and raise AssertionError to fail.

    try:
        from crewai.agent.core import Agent
        from crewai.mcp import MCPConfig
    except ImportError as e:
        print("Failed to import crewAI packages - make sure you run this in the project venv.")
        print(e)
        sys.exit(1)

    # Construct a minimal MCPConfig with SSE transport that triggers the issue
    # Because the issue is an invalid argument passed to SSE transport client,
    # passing 'terminate_on_close' triggers failure

    # We simulate an MCPConfig that uses SSE transport. The config structure in crewAI may differ,
    # but from the links in the description, we expect something like:
    # MCPConfig has properties .transport and .transport_config or similar

    # We try to create an MCPConfig like this - note this might need to be adapted if MCPConfig API changed

    try:
        # Create a config dict that makes Transport = "sse"
        config = MCPConfig(
            transport="sse",
            transport_settings={
                "url": "http://localhost:5100/mcp-event",  # example endpoint
                # intentionally no terminate_on_close (or we do if forced)
            }
        )

        # create Agent
        agent = Agent(name="reproducer-agent")

        # call get_mcp_tools with config that causes crash on attempting SSE client creation
        # The fault is inside _get_native_mcp_tools called from get_mcp_tools
        # It raises UnboundLocalError if invalid argument passed on SSE transport client init.

        # This is a direct reproducer: call agent.get_mcp_tools(mcps=[config])
        # expecting an Exception if issue is present

        tools = agent.get_mcp_tools(mcps=[config])
        # if no exception then issue likely fixed

    except Exception as e:
        # issue reproduced, print stack trace and assert failure
        print_stacktrace(e)
        # Raise AssertionError so test fails
        raise AssertionError(
            "Issue reproduced: exception raised when creating MCP client with SSE transport"
        ) from e

    # No exception raised
    print("No issue detected: MCP client with SSE transport did not raise an error.")
    sys.exit(0)


if __name__ == "__main__":
    main()
```
