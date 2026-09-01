```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import Any, AsyncGenerator, Callable
from agentscope.middleware._base import MiddlewareBase
from agentscope.message import HintBlock, AssistantMsg
from agentscope.event import HintBlockEvent


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
        agent: "Agent",
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator[Any, None]],
    ) -> AsyncGenerator[Any, None]:
        # Accumulate token usage from agent.state.context messages
        total_tokens = 0
        for msg in getattr(agent.state, "context", []):
            if hasattr(msg, "usage") and msg.usage is not None:
                input_tokens = getattr(msg.usage, "input_tokens", 0)
                output_tokens = getattr(msg.usage, "output_tokens", 0)
                total_tokens += input_tokens + output_tokens

        # If token usage exceeds max_tokens, inject hint message
        if total_tokens >= self.max_tokens:
            # Create a HintBlock event to inject as a hint message
            hint_block = HintBlock(
                id="budget_control_hint",
                hint=self.hint_message,
                source=None,
            )

            # Append the hint block to the last assistant message in context if possible
            context = getattr(agent.state, "context", [])
            if context:
                last_msg = context[-1]
                if isinstance(last_msg, AssistantMsg):
                    # Append hint block to existing content list or create list if content is a string
                    if isinstance(last_msg.content, str):
                        last_msg.content = [last_msg.content, hint_block]
                    elif isinstance(last_msg.content, list):
                        last_msg.content.append(hint_block)
                    else:
                        last_msg.content = [hint_block]
                else:
                    # If last_msg is not assistant, append a new AssistantMsg to context
                    context.append(
                        AssistantMsg(
                            id="budget_control_hint_msg",
                            name=agent.name,
                            content=[hint_block],
                        )
                    )
            else:
                # No context found, create new context with assistant message
                agent.state.context = [
                    AssistantMsg(
                        id="budget_control_hint_msg",
                        name=agent.name,
                        content=[hint_block],
                    )
                ]

            # Optionally, inject a flag or adjust input_kwargs to indicate budget reached
            input_kwargs = dict(input_kwargs)  # shallow copy
            input_kwargs["token_budget_reached"] = True

        # Continue reasoning, yield all events from next_handler
        async for event in next_handler():
            yield event
</patched>
```