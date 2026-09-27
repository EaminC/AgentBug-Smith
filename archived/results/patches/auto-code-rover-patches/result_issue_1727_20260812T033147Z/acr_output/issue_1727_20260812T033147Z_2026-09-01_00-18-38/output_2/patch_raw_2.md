```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import AsyncGenerator, Callable
from src.agentscope.middleware._base import MiddlewareBase
from src.agentscope.message._base import Msg

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
        self.total_tokens = 0  # Tracks total token usage

    async def on_reasoning(
        self,
        agent,
        input_kwargs: dict,
        next_handler: Callable[[], AsyncGenerator],
    ) -> AsyncGenerator:
        """
        Middleware hook to control total token usage during reasoning steps.
        Accumulates tokens from the current reply message before each step.
        If usage exceeds the max_tokens budget, injects a hint message
        instructing the agent to wrap up immediately.
        """
        # Attempt to access the current reply message from input_kwargs or agent state
        reply_msg = input_kwargs.get("reply_msg") or getattr(agent, "reply_msg", None)

        # Accumulate tokens from the current message usage if available
        if isinstance(reply_msg, Msg) and reply_msg.usage:
            usage = reply_msg.usage
            current_total = usage.input_tokens + usage.output_tokens
            self.total_tokens += current_total

        # If token budget exceeded, inject a hint message before continuing
        if self.total_tokens >= self.max_tokens:
            # Inject hint message into input_kwargs to signal completion
            hints = input_kwargs.setdefault("hints", [])
            hints.append(self.hint_message)

        # Continue with the reasoning step and yield events
        async for event in next_handler():
            yield event
</patched>
```