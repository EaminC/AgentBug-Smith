```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import Any, AsyncGenerator, Callable, cast

from ..middleware._base import MiddlewareBase
from ..agent import Agent
from ..message import Msg


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

    async def on_reasoning(
        self,
        agent: Agent,
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator[Any, None]],
    ) -> AsyncGenerator[Any, None]:
        """
        Middleware hook to enforce token budget control.

        Accumulates total token usage from agent.state.context messages.
        If token usage exceeds max_tokens, injects a hint message instructing
        the agent to stop reasoning normally and conclude.

        Yields events from downstream reasoning while applying this control.
        """
        # Calculate total tokens used so far by summing usage in context messages
        total_tokens = 0
        for msg in getattr(agent.state, "context", []):
            # msg may be of type Msg or a subclass
            usage = getattr(msg, "usage", None)
            if usage is not None:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
                total_tokens += input_tokens + output_tokens

        if total_tokens >= self.max_tokens:
            # Inject hint message to instruct agent to wrap up immediately.
            # Append to the input kwargs so the agent can observe it.
            # Assuming the reasoning input includes a prompt or initial messages.
            # We add a special key "__budget_hint" or similar.
            budget_hint_key = "__budget_hint"
            existing_hint = input_kwargs.get(budget_hint_key, "")
            new_hint = self.hint_message
            if existing_hint:
                new_hint = f"{existing_hint}\n{self.hint_message}"
            input_kwargs = dict(input_kwargs)  # Make a shallow copy
            input_kwargs[budget_hint_key] = new_hint

        # Continue with downstream reasoning
        async for event in next_handler(**input_kwargs):
            yield event
</patched>
```