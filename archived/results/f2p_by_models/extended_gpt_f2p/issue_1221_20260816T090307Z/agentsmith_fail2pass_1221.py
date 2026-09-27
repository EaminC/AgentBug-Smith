import pytest
from datetime import timedelta
from strands.tools.mcp import MCPClient
from mcp.client.stdio import stdio_client, StdioServerParameters
from unittest.mock import patch


def test_mcp_client_connection_stability_with_client_timeout():
    """
    Integration test to verify that MCPClient connection remains stable when multiple tool calls
    timeout on the client side and late responses arrive from the server.

    This test triggers multiple calls with very small timeouts to cause client-side timeouts,
    which produce "unknown request id" errors internally. The client should ignore these non-fatal
    errors and keep the connection alive, allowing subsequent calls to succeed.

    The test fails on the buggy codebase because the connection collapses on late responses,
    causing exceptions and failed calls. After the fix, the connection stays alive and all calls
    behave as expected.
    """
    stdio_mcp_client = MCPClient(
        lambda: stdio_client(StdioServerParameters(command="python", args=["tests_integ/mcp/echo_server.py"]))
    )

    with stdio_mcp_client:
        # Spy on the debug logger to capture non-fatal error messages
        with patch.object(stdio_mcp_client, "_log_debug_with_thread") as mock_log:
            # Make multiple calls with very small timeout to trigger "unknown request id" errors
            for i in range(3):
                try:
                    result = stdio_mcp_client.call_tool_sync(
                        tool_use_id=f"test_{i}",
                        name="echo",
                        arguments={"to_echo": f"test_{i}"},
                        read_timeout_seconds=timedelta(milliseconds=0),  # Very small timeout to force timeout
                    )
                except Exception:
                    # Ignore exceptions here; we are testing connection stability
                    pass

            # Verify connection is still alive by making a successful call
            result = stdio_mcp_client.call_tool_sync(
                tool_use_id="final_test", name="echo", arguments={"to_echo": "connection_alive"}
            )
            assert result["status"] == "success"
            assert result["content"][0]["text"] == "connection_alive"

            # Verify that non-fatal error messages were logged at least once
            assert any("ignoring non-fatal MCP session error" in str(call) for call in mock_log.call_args_list)
