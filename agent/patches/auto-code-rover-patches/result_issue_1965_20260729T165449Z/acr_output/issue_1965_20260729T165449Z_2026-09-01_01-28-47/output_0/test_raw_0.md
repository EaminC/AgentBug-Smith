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

sys.path.insert(0, "src")
sys.path.insert(0, "tests")

from utils import MockModel
from agentscope.agent import Agent
from agentscope.middleware import MiddlewareBase
from agentscope.message import UserMsg, TextBlock
from agentscope.model import ChatResponse
from agentscope.tool import Toolkit


received_messages = []


class TrackingModel(MockModel):
    async def _call_api(self, *args, **kwargs):
        # Collect all messages passed in 'messages' kwarg to verify flow
        received_messages.extend(kwargs.get("messages", []))
        return await super()._call_api(*args, **kwargs)


class OuterModifyMiddleware(MiddlewareBase):
    async def on_reply(self, agent, input_kwargs, next_handler):
        # Replace input 'inputs' with a modified UserMsg, then call next_handler passing the new inputs explicitly
        modified = UserMsg("user", "MODIFIED")
        async for item in next_handler(inputs=modified):
            yield item


class InnerTransparentMiddleware(MiddlewareBase):
    async def on_reply(self, agent, input_kwargs, next_handler):
        # Print input content seen here (should be "MODIFIED", verifying forward of modified inputs)
        print("inner sees:", input_kwargs["inputs"].get_text_content())
        # Call next_handler without kwargs: if issue present, original inputs come downstream instead of the modified one
        async for item in next_handler():
            yield item


async def main():
    model = TrackingModel()
    model.set_responses([
        ChatResponse(content=[TextBlock(text="ok")], is_last=True),
    ])

    agent = Agent(
        name="test_agent",
        system_prompt="test prompt",
        model=model,
        toolkit=Toolkit(),
        middlewares=[
            OuterModifyMiddleware(),
            InnerTransparentMiddleware(),
        ],
    )

    await agent.reply(UserMsg("user", "ORIGINAL"))

    user_messages = [m for m in received_messages if m.role == "user"]
    received_text = user_messages[-1].get_text_content()

    expected = "MODIFIED"
    try:
        assert received_text == expected, (
            f"Test failed: expected model to receive '{expected}', but got '{received_text}'"
        )
    except AssertionError as e:
        print_stacktrace(e)
        # Exit with non-zero status to indicate failure
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```
