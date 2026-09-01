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


import sys
import asyncio
from typing import Awaitable, Protocol, runtime_checkable, Union

try:
    # Try to import the Plugin protocol from the expected path.
    # According to the issue, Plugin is defined in strands.plugins.plugin and exported from strands.hooks and top-level strands.
    # We try top-level import first to simulate usage as a consumer.
    from strands import Plugin
    from strands.plugins.plugin import Plugin as PluginDirect
except ImportError as e:
    print(f"ImportError: {e}", file=sys.stderr)
    print("Make sure the Plugin Protocol is defined and exported as required.", file=sys.stderr)
    sys.exit(1)

# We need an Agent stub class compatible with the protocol's type hints, minimal.
class Agent:
    def add_hook(self, callback, event_type):
        pass  # dummy method to satisfy plugin example usage


# Now test that Plugin protocol matches sync and async implementations.

class SyncPlugin:
    name = "sync-test-plugin"

    def init_plugin(self, agent: Agent) -> None:
        # simulate synchronous init
        agent.add_hook(lambda e: None, object)


class AsyncPlugin:
    name = "async-test-plugin"

    async def init_plugin(self, agent: Agent) -> None:
        # simulate async init
        await asyncio.sleep(0.001)
        agent.add_hook(lambda e: None, object)


def check_isinstance(plugin_instance, proto, expect: bool, label: str):
    try:
        result = isinstance(plugin_instance, proto)
        assert result is expect, f"{label} instance check mismatch: expected {expect}, got {result}"
    except Exception as e:
        print(f"Error during isinstance check of {label}:")
        print_stacktrace(e)
        raise


async def async_init_plugin_call(plugin: Plugin, agent: Agent):
    ret = plugin.init_plugin(agent)
    # ret can be None or Awaitable
    if ret is not None:
        # Awaitable expected
        await ret


def main():
    agent = Agent()

    # 1) Check that Plugin is a runtime checkable Protocol and isinstance works as expected.

    # Should be true for both sync and async implementations
    try:
        check_isinstance(SyncPlugin(), Plugin, True, "SyncPlugin")
        check_isinstance(AsyncPlugin(), Plugin, True, "AsyncPlugin")
    except AssertionError as e:
        # Print stacktrace and exit 1 - indicates the issue is present
        print_stacktrace(e)
        sys.exit(1)

    # 2) Check calling init_plugin works for sync impl (returns None)
    sync_plugin = SyncPlugin()
    try:
        ret = sync_plugin.init_plugin(agent)
        assert ret is None, "SyncPlugin.init_plugin should return None"
    except Exception as e:
        print("SyncPlugin.init_plugin failed:")
        print_stacktrace(e)
        sys.exit(1)

    # 3) Check calling init_plugin works for async impl (returns Awaitable)
    async_plugin = AsyncPlugin()

    try:
        ret = async_plugin.init_plugin(agent)
        # ret must be Awaitable, check with asyncio.isfuture or asyncio.iscoroutine
        import asyncio
        assert asyncio.iscoroutine(ret), "AsyncPlugin.init_plugin should return coroutine"
    except Exception as e:
        print("AsyncPlugin.init_plugin failed:")
        print_stacktrace(e)
        sys.exit(1)

    # 4) Await async init_plugin successfully
    try:
        asyncio.run(async_init_plugin_call(async_plugin, agent))
    except Exception as e:
        print("Failed awaiting init_plugin of AsyncPlugin:")
        print_stacktrace(e)
        sys.exit(1)

    # If all tests passed
    print("All Plugin protocol checks passed. Issue not present.")

if __name__ == "__main__":
    main()
```
