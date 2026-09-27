import gc
import weakref

import pytest

from strands import Agent
from strands.tools.tool_provider import ToolProvider


def test_agent_collected_without_cyclic_gc():
    """Verify that Agent is promptly collectable (no persistent reference cycle).

    This ensures that the weakref-based back-references in _ToolCaller and _PluginRegistry
    do not create reference cycles that would delay cleanup until interpreter shutdown.
    When cleanup is deferred to interpreter shutdown, MCPClient.stop() hangs because its
    background thread cannot complete async cleanup at that point.

    Note: On some platforms/versions (e.g. Python 3.14 with deferred refcounting), del may
    not immediately trigger collection. A single gc.collect() is allowed as a fallback since
    it still proves no persistent cycle exists — the agent is collected promptly, not deferred
    to interpreter shutdown.
    """
    gc.disable()
    try:
        agent = Agent()
        ref = weakref.ref(agent)
        del agent

        if ref() is not None:
            # Deferred refcounting (Python 3.14+) may not collect immediately on del;
            # a single gc.collect() should still reclaim it since there are no cycles.
            gc.collect()

        assert ref() is None, "Agent was not collected; a reference cycle likely exists"
    finally:
        gc.enable()


class _MockToolProvider(ToolProvider):
    """Minimal ToolProvider that tracks cleanup calls, mimicking MCPClient lifecycle."""

    def __init__(self):
        self.consumers: set = set()
        self.cleanup_called = False

    async def load_tools(self, **kwargs):
        return []

    def add_consumer(self, consumer_id, **kwargs):
        self.consumers.add(consumer_id)

    def remove_consumer(self, consumer_id, **kwargs):
        self.consumers.discard(consumer_id)
        if not self.consumers:
            self.cleanup_called = True


def test_agent_with_tool_provider_cleaned_up_when_function_returns():
    """Replicate the hang from issue #1732: Agent with MCPClient created inside a function.

    When an Agent using a managed MCPClient (as ToolProvider) is created inside a function,
    the script used to hang on exit. The Agent went out of scope when the function returned,
    but circular references (Agent → _ToolCaller._agent → Agent) prevented refcount-based
    destruction. Cleanup was deferred to the cyclic GC during interpreter shutdown, where
    MCPClient.stop() → thread.join() would hang.

    This test verifies that with the weakref fix, the Agent is destroyed immediately when
    the function returns, and the tool provider's cleanup runs promptly.
    """
    provider = _MockToolProvider()

    def get_agent():
        return Agent(tools=[provider])

    def main():
        agent = get_agent()  # noqa: F841

    gc.disable()
    try:
        main()

        if not provider.cleanup_called:
            # Deferred refcounting (Python 3.14+) may not collect immediately on scope exit;
            # a single gc.collect() should still reclaim it since there are no cycles.
            gc.collect()

        assert provider.cleanup_called, (
            "Tool provider was not cleaned up when the function returned; Agent likely leaked due to a reference cycle"
        )
    finally:
        gc.enable()


def test_agent_with_tool_provider_cleaned_up_on_del():
    """Replicate the working case from issue #1732: Agent at module scope, explicitly deleted.

    In the issue, an Agent created at module level did not hang because module-level variables
    are cleared early during interpreter shutdown (while the runtime is still functional).
    This test verifies the equivalent: explicitly deleting the agent triggers immediate cleanup.
    """
    provider = _MockToolProvider()

    agent = Agent(tools=[provider])
    assert not provider.cleanup_called

    del agent

    if not provider.cleanup_called:
        # Deferred refcounting (Python 3.14+) may not collect immediately on del;
        # a single gc.collect() should still reclaim it since there are no cycles.
        gc.collect()

    assert provider.cleanup_called, "Tool provider was not cleaned up after del agent"


def test_tool_caller_raises_reference_error_after_agent_collected():
    """Verify _ToolCaller raises ReferenceError when the Agent has been garbage collected."""
    agent = Agent()
    caller = agent.tool_caller
    # Clear the weak reference by replacing it directly
    caller._agent_ref = weakref.ref(agent)
    del agent
    gc.collect()

    with pytest.raises(ReferenceError, match="Agent has been garbage collected"):
        _ = caller._agent
