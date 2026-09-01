Reasoning:

The issue is that with `window_size=0`, the trimming logic in `reduce_context` silently fails or raises exceptions instead of clearing all messages, as the TypeScript SDK behavior expects. To fix this, we have two valid approaches according to the issue description:

1. Reject `window_size=0` at initialization, raising a `ValueError`.
2. Add special handling in `reduce_context` to immediately clear all messages if `window_size=0`.

Because the existing code does not currently reject `window_size=0`, and the issue's expectation is aligned with the TypeScript SDK which treats `window_size=0` as "clear all messages," it is more user-friendly to support that behavior here (option 2).

Hence, in `reduce_context`, early in the method, I will add a check: if `window_size == 0`, clear all messages immediately and return. This will directly address the problem without interfering with the existing logic for positive window sizes.

No changes to `__init__` are necessary, but optionally, we can explicitly allow `window_size` to be zero as a valid parameter.

---

Patch:

```
<file>src/strands/agent/conversation_manager/sliding_window_conversation_manager.py</file>
<original>    def reduce_context(self, agent: "Agent", e: Exception | None = None, **kwargs: Any) -> None:
        """Trim the oldest messages to reduce the conversation context size.

        The method handles special cases where trimming the messages leads to:
         - toolResult with no corresponding toolUse
         - toolUse with no corresponding toolResult

        Args:
            agent: The agent whose messages will be reduce.
                This list is modified in-place.
            e: The exception that triggered the context reduction, if any.
            **kwargs: Additional keyword arguments for future extensibility.

        Raises:
            ContextWindowOverflowException: If the context cannot be reduced further and a context overflow
                error was provided (e is not None). When called during routine window management (e is None),
                logs a warning and returns without modification.
        """
        messages = agent.messages

        # Try to truncate the tool result first
        oldest_message_idx_with_tool_results = self._find_oldest_message_with_tool_results(messages)
        if oldest_message_idx_with_tool_results is not None and self.should_truncate_results:
            logger.debug(
                "message_index=<%s> | found message with tool results at index", oldest_message_idx_with_tool_results
            )
            results_truncated = self._truncate_tool_results(messages, oldest_message_idx_with_tool_results)
            if results_truncated:
                logger.debug("message_index=<%s> | tool results truncated", oldest_message_idx_with_tool_results)
                return

        # Try to trim index id when tool result cannot be truncated anymore
        # If the number of messages is less than the window_size, then we default to 2, otherwise, trim to window size
        trim_index = 2 if len(messages) <= self.window_size else len(messages) - self.window_size

        # Find the next valid trim point that:
        # 1. Starts with a user message (required by most model providers)
        # 2. Does not start with an orphaned toolResult
        # 3. Does not start with a toolUse unless its toolResult immediately follows
        # Falls back to an assistant(toolUse) + user(toolResult) boundary if no plain user message exists.
        # This is acceptable because providers treat a complete toolUse/toolResult pair as a valid
        # conversation continuation, and without this fallback tool-heavy conversations cannot be trimmed.
        fallback_trim_index = None

        while trim_index < len(messages):
            # Prefer starting with a user message
            if messages[trim_index]["role"] != "user":
                # Track first valid assistant(toolUse) + user(toolResult) pair as fallback
                if (
                    fallback_trim_index is None
                    and any("toolUse" in content for content in messages[trim_index]["content"])
                    and trim_index + 1 < len(messages)
                    and messages[trim_index + 1]["role"] == "user"
                    and any("toolResult" in content for content in messages[trim_index + 1]["content"])
                ):
                    fallback_trim_index = trim_index

                trim_index += 1
                continue

            if (
                # Oldest message cannot be a toolResult because it needs a toolUse preceding it
                any("toolResult" in content for content in messages[trim_index]["content"])
                or (
                    # Oldest message can be a toolUse only if a toolResult immediately follows it.
                    # Note: toolUse content normally appears only in assistant messages, but this
                    # check is kept as a defensive safeguard for non-standard message formats.
                    any("toolUse" in content for content in messages[trim_index]["content"])
                    and not (
                        trim_index + 1 < len(messages)
                        and any("toolResult" in content for content in messages[trim_index + 1]["content"])
                    )
                )
            ):
                trim_index += 1
            else:
                break
        else:
            # No plain user message found — use assistant+toolResult fallback if available
            if fallback_trim_index is not None:
                logger.debug(
                    "trim_index=<%s> | no plain user message trim point found, "
                    "falling back to assistant(toolUse) + user(toolResult) boundary",
                    fallback_trim_index,
                )
                trim_index = fallback_trim_index
            elif e is not None:
                raise ContextWindowOverflowException("Unable to trim conversation context!") from e
            else:
                logger.warning(
                    "window_size=<%s>, message_count=<%s> | unable to trim conversation context, "
                    "no valid trim point found",
                    self.window_size,
                    len(messages),
                )
                return

        # trim_index represents the number of messages being removed from the agents messages array
        self.removed_message_count += trim_index

        # Overwrite message history
        messages[:] = messages[trim_index:]</original>
<patched>    def reduce_context(self, agent: "Agent", e: Exception | None = None, **kwargs: Any) -> None:
        """Trim the oldest messages to reduce the conversation context size.

        The method handles special cases where trimming the messages leads to:
         - toolResult with no corresponding toolUse
         - toolUse with no corresponding toolResult

        Args:
            agent: The agent whose messages will be reduce.
                This list is modified in-place.
            e: The exception that triggered the context reduction, if any.
            **kwargs: Additional keyword arguments for future extensibility.

        Raises:
            ContextWindowOverflowException: If the context cannot be reduced further and a context overflow
                error was provided (e is not None). When called during routine window management (e is None),
                logs a warning and returns without modification.
        """
        messages = agent.messages

        # Special case: window_size=0 means clear all messages immediately
        if self.window_size == 0:
            self.removed_message_count += len(messages)
            messages.clear()
            return

        # Try to truncate the tool result first
        oldest_message_idx_with_tool_results = self._find_oldest_message_with_tool_results(messages)
        if oldest_message_idx_with_tool_results is not None and self.should_truncate_results:
            logger.debug(
                "message_index=<%s> | found message with tool results at index", oldest_message_idx_with_tool_results
            )
            results_truncated = self._truncate_tool_results(messages, oldest_message_idx_with_tool_results)
            if results_truncated:
                logger.debug("message_index=<%s> | tool results truncated", oldest_message_idx_with_tool_results)
                return

        # Try to trim index id when tool result cannot be truncated anymore
        # If the number of messages is less than the window_size, then we default to 2, otherwise, trim to window size
        trim_index = 2 if len(messages) <= self.window_size else len(messages) - self.window_size

        # Find the next valid trim point that:
        # 1. Starts with a user message (required by most model providers)
        # 2. Does not start with an orphaned toolResult
        # 3. Does not start with a toolUse unless its toolResult immediately follows
        # Falls back to an assistant(toolUse) + user(toolResult) boundary if no plain user message exists.
        # This is acceptable because providers treat a complete toolUse/toolResult pair as a valid
        # conversation continuation, and without this fallback tool-heavy conversations cannot be trimmed.
        fallback_trim_index = None

        while trim_index < len(messages):
            # Prefer starting with a user message
            if messages[trim_index]["role"] != "user":
                # Track first valid assistant(toolUse) + user(toolResult) pair as fallback
                if (
                    fallback_trim_index is None
                    and any("toolUse" in content for content in messages[trim_index]["content"])
                    and trim_index + 1 < len(messages)
                    and messages[trim_index + 1]["role"] == "user"
                    and any("toolResult" in content for content in messages[trim_index + 1]["content"])
                ):
                    fallback_trim_index = trim_index

                trim_index += 1
                continue

            if (
                # Oldest message cannot be a toolResult because it needs a toolUse preceding it
                any("toolResult" in content for content in messages[trim_index]["content"])
                or (
                    # Oldest message can be a toolUse only if a toolResult immediately follows it.
                    # Note: toolUse content normally appears only in assistant messages, but this
                    # check is kept as a defensive safeguard for non-standard message formats.
                    any("toolUse" in content for content in messages[trim_index]["content"])
                    and not (
                        trim_index + 1 < len(messages)
                        and any("toolResult" in content for content in messages[trim_index + 1]["content"])
                    )
                )
            ):
                trim_index += 1
            else:
                break
        else:
            # No plain user message found — use assistant+toolResult fallback if available
            if fallback_trim_index is not None:
                logger.debug(
                    "trim_index=<%s> | no plain user message trim point found, "
                    "falling back to assistant(toolUse) + user(toolResult) boundary",
                    fallback_trim_index,
                )
                trim_index = fallback_trim_index
            elif e is not None:
                raise ContextWindowOverflowException("Unable to trim conversation context!") from e
            else:
                logger.warning(
                    "window_size=<%s>, message_count=<%s> | unable to trim conversation context, "
                    "no valid trim point found",
                    self.window_size,
                    len(messages),
                )
                return

        # trim_index represents the number of messages being removed from the agents messages array
        self.removed_message_count += trim_index

        # Overwrite message history
        messages[:] = messages[trim_index:]
</patched>
```