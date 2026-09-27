```
<file>src/agentscope/middleware/budget_control_middleware.py</file>
<original></original>
<patched>from typing import AsyncGenerator, Callable
from src.agentscope.middleware._base import MiddlewareBase
from src.agentscope.message._base import Msg, HintBlock

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
        self._accumulated_tokens = 0

    async def on_reasoning(
        self,
        agent,
        input_kwargs: dict,
        next_handler: Callable[..., AsyncGenerator],
    ) -> AsyncGenerator:
        # Accumulate token usage from agent state or messages
        # We expect the agent's state or context to provide the current Msg reply or usage info
        # For demonstration, try to accumulate tokens from the current reply message usage

        # Reset accumulated tokens at start
        self._accumulated_tokens = 0

        # Attempt to accumulate tokens from agent.state or input_kwargs - this depends on implementation
        # Here, try to get the current reply or messages token usage from agent.state or input_kwargs that represent current Msg(s)
        # This is a heuristic/example and may adjust depending on actual agent state API.

        # If input_kwargs contains "messages" or "inputs", we get the last Msg usage
        messages = input_kwargs.get("messages") or input_kwargs.get("inputs")
        if messages:
            # messages may be a list or a single Msg
            if isinstance(messages, list):
                for msg in messages:
                    usage = getattr(msg, "usage", None)
                    if usage:
                        self._accumulated_tokens += getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)
            else:
                usage = getattr(messages, "usage", None)
                if usage:
                    self._accumulated_tokens += getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)

        # Check token budget exceed
        if self._accumulated_tokens >= self.max_tokens:
            # Inject hint message before reasoning to prompt agent to conclude
            hint = HintBlock(
                id="budget_hint",
                hint=self.hint_message,
                source="BudgetControlMiddleware",
            )
            # Yield the hint message as an event for agent to process
            yield hint
            # Do not proceed further to next_handler to avoid tool calls
            return

        # Otherwise, just yield events from next_handler as usual, allowing reasoning to continue
        async for event in next_handler():
            # Before yielding, if event is a Msg with token usage, accumulate tokens
            # This allows dynamic accumulation during reasoning
            if isinstance(event, Msg):
                usage = getattr(event, "usage", None)
                if usage:
                    self._accumulated_tokens += getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)
                    if self._accumulated_tokens >= self.max_tokens:
                        # After yielding this event, inject hint to stop reasoning
                        yield event
                        hint = HintBlock(
                            id="budget_hint",
                            hint=self.hint_message,
                            source="BudgetControlMiddleware",
                        )
                        yield hint
                        return
            yield event
</patched>
```
