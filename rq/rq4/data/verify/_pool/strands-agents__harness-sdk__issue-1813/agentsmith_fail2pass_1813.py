import contextvars
import threading
from concurrent import futures

import pytest

from strands.tools.mcp.mcp_client import MCPClient
from strands.types.exceptions import MCPClientInitializationError


@pytest.mark.asyncio
async def test_server_instructions_exposed_after_startup(monkeypatch):
    """
    This test verifies that MCPClient.server_instructions is set correctly
    from the InitializeResult returned by session.initialize().

    Fail2pass behavior:
    - Before the fix, MCPClient does not expose server_instructions, so this test fails.
    - After the fix, server_instructions is set and accessible, so this test passes.
    """

    class DummyInitializeResult:
        def __init__(self):
            self.instructions = "Server instructions for testing."

    class DummySession:
        async def initialize(self):
            return DummyInitializeResult()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        def get_server_capabilities(self):
            # Return dummy capabilities to avoid AttributeError in MCPClient._async_background_thread
            return None

    class DummyClientSessionContextManager:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    # Patch ClientSession to return our dummy session context manager
    monkeypatch.setattr(
        "strands.tools.mcp.mcp_client.ClientSession",
        lambda *args, **kwargs: DummyClientSessionContextManager(),
    )

    def dummy_transport_callable():
        class DummyTransportCM:
            async def __aenter__(self):
                return (None, None)

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return DummyTransportCM()

    # Use the dummy transport callable to create MCPClient
    with MCPClient(dummy_transport_callable) as client:
        # The background thread should have run and set server_instructions
        assert client.server_instructions == "Server instructions for testing."


def test_server_instructions_none_when_initialize_returns_none(monkeypatch):
    """
    This test verifies that MCPClient.server_instructions is None when
    the server returns None instructions.

    Fail2pass behavior:
    - Before the fix, server_instructions attribute may not exist or may be None,
      so this test may fail if attribute is missing or incorrectly set.
    - After the fix, server_instructions is set to None properly.
    """

    class DummyInitializeResult:
        def __init__(self):
            self.instructions = None

    class DummySession:
        async def initialize(self):
            return DummyInitializeResult()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        def get_server_capabilities(self):
            # Return dummy capabilities to avoid AttributeError in MCPClient._async_background_thread
            return None

    class DummyClientSessionContextManager:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        "strands.tools.mcp.mcp_client.ClientSession",
        lambda *args, **kwargs: DummyClientSessionContextManager(),
    )

    def dummy_transport_callable():
        class DummyTransportCM:
            async def __aenter__(self):
                return (None, None)

            async def __aexit__(self, exc_type, exc, tb):
                pass

        return DummyTransportCM()

    with MCPClient(dummy_transport_callable) as client:
        assert client.server_instructions is None
