```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import AsyncGenerator, Callable
from agentscope.middleware._base import MiddlewareBase
from agentscope.message._base import Msg

class BudgetControlMiddleware(MiddlewareBase):
    def __init__(
        self,
        max_tokens: int,
        hint_message: str = (
            "You have reached the maximum token budget. "
            "Please wrap up immediately and provide a final "
            "concluding response without invoking any tools."
        ),
    ) -> None:
        self.max_tokens = max_tokens
        self.hint_message = hint_message
        self._total_tokens = 0

    async def on_reasoning(
        self,
        agent,
        input_kwargs: dict,
        next_handler: Callable[[], AsyncGenerator],
    ) -> AsyncGenerator:
        # Accumulate token usage from the last reply message if any
        reply_msg = getattr(agent.state, "last_reply", None)
        if reply_msg is None or not isinstance(reply_msg, Msg):
            # Fallback: try to get the reply message from input_kwargs
            reply_msg = input_kwargs.get("msg")
            if reply_msg is None or not isinstance(reply_msg, Msg):
                # Could not find reply message to get token usage, proceed normally
                async for event in next_handler():
                    yield event
                return

        # Sum input and output tokens if usage is available
        usage = reply_msg.usage
        if usage:
            current_tokens = usage.input_tokens + usage.output_tokens
            self._total_tokens += current_tokens

        if self._total_tokens > self.max_tokens:
            # Inject hint message to input_kwargs to tell agent to wrap up
            content = input_kwargs.get("content", "")
            if content:
                content = f"{self.hint_message}\n{content}"
            else:
                content = self.hint_message
            input_kwargs["content"] = content

            # Also, if there is a messages list, prepend a hint message block
            messages = input_kwargs.get("messages")
            if messages is not None and isinstance(messages, list):
                from agentscope.message._base import Msg
                hint_msg = Msg()  # Create a new empty message
                # Insert the hint message's content as a special hint block or text
                # Since there is no direct constructor param for hint, append a hint block
                from agentscope.message._base import HintBlock
                hint_block = HintBlock(
                    id="budget_hint",
                    source=None,
                    hint=self.hint_message,
                )
                hint_msg.content.append(hint_block)
                messages.insert(0, hint_msg)

        async for event in next_handler():
            yield event
</patched>
```