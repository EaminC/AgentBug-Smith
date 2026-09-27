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


def main():
    import sys
    import asyncio
    import inspect

    # We import Agent, Plugin, AgentInitializedEvent and run_async from strands.
    # We assume these imports exist in the project structure according to the issue.
    try:
        from strands import Agent, Plugin
        from strands.hooks import AgentInitializedEvent
        # run_async helper is supposed to be imported implicitly in agent.py,
        # but here we import from strands.agent.agent for testing
        from strands.agent.agent import run_async
    except ImportError as e:
        print("Failed to import necessary modules. Make sure you run this in the project root and dependencies installed.")
        print_stacktrace(e)
        sys.exit(1)

    # Test plugin with sync init_plugin
    class SyncPlugin:
        name = "sync"

        def __init__(self):
            self.initialized_with = None

        def init_plugin(self, agent):
            # Just record the agent instance for test
            self.initialized_with = agent

    # Test plugin with async init_plugin
    class AsyncPlugin:
        name = "async"

        def __init__(self):
            self.initialized_with = None

        async def init_plugin(self, agent):
            # Simulate async work
            await asyncio.sleep(0.001)
            self.initialized_with = agent

    # Track order of initialization by modifying init_plugin methods to log calls
    initialization_order = []

    class OrderSyncPlugin:
        name = "order_sync"

        def init_plugin(self, agent):
            initialization_order.append(self.name)

    class OrderAsyncPlugin:
        name = "order_async"

        async def init_plugin(self, agent):
            # simulate async delay
            await asyncio.sleep(0.001)
            initialization_order.append(self.name)

    try:
        # Create sync and async plugin instances
        sync_plugin = SyncPlugin()
        async_plugin = AsyncPlugin()

        # Also create order test plugins
        order_sync_plugin = OrderSyncPlugin()
        order_async_plugin = OrderAsyncPlugin()

        # Create agent with plugins param including both sync and async plugins
        # We'll wrap the async init_plugin calls with run_async, so no explicit async code here.
        # The agent should call init_plugin on each plugin at construction time.

        agent = Agent(
            plugins=[sync_plugin, async_plugin, order_sync_plugin, order_async_plugin],
        )

    except Exception as e:
        # If an exception occurs, print stacktrace and mark failure
        print_stacktrace(e)
        raise AssertionError("Agent failed to initialize plugins properly") from e

    # Now verify sync plugin initialized properly
    if sync_plugin.initialized_with is not agent:
        raise AssertionError("Sync plugin init_plugin was not called correctly.")

    # For async plugin, if initialized_with is None, either async init_plugin wasn't awaited properly or run_async not called
    if async_plugin.initialized_with is not agent:
        raise AssertionError("Async plugin init_plugin was not called correctly.")

    # Verify order list length and values
    # Expect initialization_order to have ["order_sync", "order_async"] in that order
    # Because sync plugin initialized first, then async plugin, then ordered sync, then ordered async,
    # the order plugins were last two, should have their init_plugins called in order

    # Since in __init__ plugins block, plugins go in this order:
    # 1. sync_plugin (records initialized_with)
    # 2. async_plugin (records initialized_with async)
    # 3. order_sync_plugin (appends "order_sync")
    # 4. order_async_plugin (appends "order_async" async)

    # So initialization_order should be ["order_sync", "order_async"]
    # Wait a very short time here to allow async run_async calls to finish
    # since run_async may schedule async calls on event loop

    # The problem is run_async uses asyncio.get_event_loop().create_task or similar,
    # so the async init_plugins should have been triggered.

    # We'll try to wait a bit for the async plugins to finish
    import time
    time.sleep(0.1)

    expected_order = ["order_sync", "order_async"]
    if initialization_order != expected_order:
        raise AssertionError(f"Plugin initialization order incorrect, expected {expected_order} got {initialization_order}")

    # Test empty plugins param does not cause error (should be allowed)
    try:
        agent2 = Agent(plugins=[])
    except Exception as e:
        print_stacktrace(e)
        raise AssertionError("Agent failed initializing with empty plugins list") from e

    # Test plugins param None does not cause error (default)
    try:
        agent3 = Agent()
    except Exception as e:
        print_stacktrace(e)
        raise AssertionError("Agent failed initializing with plugins=None") from e

    # If got here, tests passed
    print("All plugin initialization tests passed.")


if __name__ == "__main__":
    import sys
    try:
        main()
    except AssertionError as e:
        # Print error message and stacktrace if available in cause
        cause = e.__cause__
        if cause:
            print_stacktrace(cause)
        else:
            print(str(e))
        sys.exit(1)
    sys.exit(0)
```
