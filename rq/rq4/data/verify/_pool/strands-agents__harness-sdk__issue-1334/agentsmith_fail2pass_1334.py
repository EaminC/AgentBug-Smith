import threading
import asyncio
import pytest

from strands.tools.mcp.mcp_client import MCPClient


class DummyThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self._alive = True

    def is_alive(self):
        return self._alive

    def stop(self):
        self._alive = False


class DummyFuture:
    def __init__(self, done: bool):
        self._done = done

    def done(self):
        return self._done


@pytest.mark.asyncio
async def test_mcpclient_does_not_hang_on_close_future_done():
    """
    This test checks that MCPClient._is_session_active returns False
    when _close_future is done, to prevent hanging on 5xx errors.

    The buggy code returns True if _background_thread is alive,
    ignoring _close_future.done(), causing hangs.

    The fixed code returns False if _close_future.done() is True,
    preventing hangs.

    We simulate the condition by creating an MCPClient instance,
    setting a dummy alive background thread, and a done _close_future,
    then calling _is_session_active and asserting it returns False.

    This test should fail on buggy code (returns True),
    and pass on fixed code (returns False).
    """

    # MCPClient requires a transport_callable argument; provide a dummy callable
    def dummy_transport_callable(*args, **kwargs):
        pass

    client = MCPClient(dummy_transport_callable)

    # Patch _background_thread to a dummy thread that is alive
    dummy_thread = DummyThread()
    client._background_thread = dummy_thread

    # Patch _close_future to a dummy future that is done
    client._close_future = DummyFuture(done=True)

    # Call the method under test
    active = client._is_session_active()

    # We expect _is_session_active to return False when _close_future.done() is True
    # Buggy code returns True here, so this assertion fails on buggy code and passes on fixed code
    assert active is False, (
        "MCPClient._is_session_active should return False when _close_future is done "
        "to prevent hanging, but it returned True."
    )
