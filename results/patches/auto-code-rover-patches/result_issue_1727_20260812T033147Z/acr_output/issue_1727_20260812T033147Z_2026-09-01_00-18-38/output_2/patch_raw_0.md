```
<file>src/agentscope/middleware/budget_control.py</file>
<original></original>
<patched>from typing import AsyncGenerator, Callable

from ..message._base import Msg
from ._base import MiddlewareBase


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
        next_handler: Callable[[], AsyncGenerator],
    ) -> AsyncGenerator:
        """
        Middleware hook to control token budget before each reasoning step.

        Accumulates token usage from the current reply message (Msg).
        If the usage exceeds the max_tokens budget, injects a hint message
        instructing the agent to immediately conclude reasoning without
        invoking any tools.
        """
        # We expect the current reply message could be found in input_kwargs or agent.state
        # This may depend on the agent's concrete implementation.
        # For generality, try to get a Msg-like object from input_kwargs or agent.state.

        # Attempt to get current reply message from input_kwargs
        reply_msg = input_kwargs.get("reply_msg", None)

        # Fallback: try to get from agent.state.context or agent.state.reply (if available)
        if reply_msg is None:
            reply_msg = getattr(agent.state, "reply", None)
        if reply_msg is None:
            reply_msg = getattr(agent.state, "context", None)

        # If reply_msg is not an instance of Msg or similar, we skip budget control
        if not isinstance(reply_msg, Msg):
            # Just forward execution if we cannot get reply message
            async for event in next_handler():
                yield event
            return

        # Calculate total tokens used so far: input_tokens + output_tokens
        usage = reply_msg.usage
        total_tokens = 0
        if usage:
            total_tokens = usage.input_tokens + usage.output_tokens

        # If token budget exceeded, inject the hint message
        if total_tokens >= self.max_tokens:
            # We prepare to inject the hint message to input_kwargs before reasoning proceeds.
            # Different agents may use different keys; "input" or "prompt" or "messages" may be used.
            # We try to handle common case: input_kwargs has "prompt" as a str, or "messages" as list of Msg

            # First try "messages" key
            messages = input_kwargs.get("messages", None)
            if messages is not None and isinstance(messages, list):
                # Append a hint Msg with hint content
                from ..message._base import HintMsg  # assuming HintMsg exists for hints
                messages.append(
                    HintMsg(
                        hint=self.hint_message,
                    )
                )
            else:
                # Otherwise try "prompt" key which might be a string
                prompt = input_kwargs.get("prompt", "")
                if isinstance(prompt, str):
                    # Append hint message to prompt string
                    prompt += f"\n\n{self.hint_message}"
                    input_kwargs["prompt"] = prompt
                else:
                    # Unknown input format, just leave as is
                    pass

        # Proceed with reasoning
        async for event in next_handler():
            yield event
</patched>
```