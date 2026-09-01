```
<file>src/agentscope/middleware/budget_control_middleware.py</file>
<original></original>
<patched>from typing import AsyncGenerator, Callable

from ._base import MiddlewareBase
from ..message._base import Msg, Usage
from ..event._event import EventType, AgentEvent, HintBlock


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
        agent,
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        """
        Middleware hook that intercepts the reasoning process.
        Before each reasoning step, accumulates token usage from the current reply messages.
        If the accumulated usage exceeds max_tokens, injects a hint message instructing the
        agent to wrap up immediately, then stops further reasoning.

        Yields:
            AgentEvent | Msg: Reasoning events, possibly including the injected hint.
        """
        # Retrieve the "inputs" argument which can be a Msg or list of Msg
        inputs = input_kwargs.get("inputs")
        # Accumulate token usage from inputs if possible
        total_tokens = 0
        if isinstance(inputs, Msg):
            if inputs.usage is not None:
                total_tokens = inputs.usage.input_tokens + inputs.usage.output_tokens
        elif isinstance(inputs, list):
            for msg in inputs:
                if isinstance(msg, Msg) and msg.usage is not None:
                    total_tokens += msg.usage.input_tokens + msg.usage.output_tokens

        if total_tokens >= self.max_tokens:
            # Construct a hint message to inject
            hint_block = HintBlock(
                id="budget_control_hint",
                hint=self.hint_message,
                source=None,
            )
            hint_msg = Msg(
                name="budget_control",
                role="system",
                content=[hint_block],
                usage=Usage(input_tokens=0, output_tokens=0),  # no tokens induced by the hint itself
            )
            # Inject the hint message before any reasoning starts, yield and end
            yield hint_msg
            # Do not call further reasoning handlers to prevent additional token consumption
            return

        # Otherwise proceed normally and yield all events from next handler
        async for event in next_handler():
            yield event
</patched>
```