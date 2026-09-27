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

import asyncio
import sys

try:
    from agentscope.agent import AgentBase
    from agentscope.message import Msg, TextBlock
    from agentscope.hooks._studio_hooks import as_studio_forward_message_pre_print_hook
except ImportError as e:
    print("Please run this script from the root directory of the project where the agentscope package is available.", file=sys.stderr)
    raise e

class TestAgent(AgentBase):
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._disable_console_output = False

    async def reply(self, msg: Msg) -> Msg:
        await self.print(msg)
        return msg

    async def observe(self, msg: Msg) -> None:
        pass

    async def handle_interrupt(self, *args, **kwargs) -> Msg:
        return Msg("test", "Interrupt handled", "assistant")

# Register hook with non-existent Studio URL to simulate disconnection
TestAgent.register_class_hook(
    "pre_print",
    "studio_forward",
    lambda self, kwargs: as_studio_forward_message_pre_print_hook(
        self, kwargs, studio_url="http://127.0.0.1:9999", run_id="test"
    ),
)

agent = TestAgent(name="TestAgent")

async def main():
    # Compose a message that will trigger the pre_print hook forwarding
    msg = Msg("user", [TextBlock(type="text", text="Hello")], "user")

    try:
        await agent.reply(msg)
    except Exception as e:
        # Print stack trace using the given function
        print_stacktrace(e)
        # The presence of the exception means issue is present => raise AssertionError
        raise AssertionError(
            "Issue reproducer caught exception (Agent crashes on Studio disconnect)"
        ) from e

if __name__ == "__main__":
    # Run the async main
    try:
        asyncio.run(main())
    except AssertionError as e:
        # Exit with code 1 when issue reproduced
        sys.exit(1)
    # If no exceptions, exit code 0 means issue fixed
    sys.exit(0)
```
