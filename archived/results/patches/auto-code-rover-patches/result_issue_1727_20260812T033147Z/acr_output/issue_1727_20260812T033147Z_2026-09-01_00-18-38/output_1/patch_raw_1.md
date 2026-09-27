```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import Any, AsyncGenerator, Callable

from agentscope.middleware._base import MiddlewareBase
from agentscope.message import HintBlock, AssistantMsg


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
        # Calculate total tokens used from agent.state.context messages
        total_input_tokens = 0
        total_output_tokens = 0
        for msg in agent.state.context:
            usage = getattr(msg, "usage", None)
            if usage:
                total_input_tokens += usage.input_tokens or 0
                total_output_tokens += usage.output_tokens or 0

        total_tokens = total_input_tokens + total_output_tokens

        # Check if token budget exceeded
        if total_tokens >= self.max_tokens:
            # Inject a hint message into the last assistant message or create new one
            if agent.state.context and isinstance(agent.state.context[-1], AssistantMsg):
                last_msg = agent.state.context[-1]
                # Append a HintBlock with the hint message
                last_msg.content.append(
                    HintBlock(
                        id="budget_control_hint",
                        hint=self.hint_message,
                    )
                )
            else:
                # No last assistant message, create one with the hint message
                agent.state.context.append(
                    AssistantMsg(
                        id="budget_control_hint_msg",
                        name=agent.name,
                        content=[
                            HintBlock(
                                id="budget_control_hint",
                                hint=self.hint_message,
                            )
                        ],
                    )
                )
            # Optionally, also inject hint message in input_kwargs or tool_choice
            input_kwargs.setdefault("system_messages", [])
            input_kwargs["system_messages"].append(self.hint_message)

        # Continue middleware chain
        async for event in next_handler():
            yield event
</patched>
```