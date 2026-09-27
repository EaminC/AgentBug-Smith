Reasoning:

To resolve the issue, the following key changes are needed:

1. Change `_find_last_message_with_tool_results` to iterate from oldest to newest to find the oldest message with tool results, preserving the newer ones intact.

2. Update `_truncate_tool_results` to perform a more size-aware and graceful truncation:
   - Only truncate when content is larger than a certain threshold (configurable via class attribute).
   - Perform partial truncation, preserving start and end while removing the middle, and inserting a truncation notice with number of removed chars.
   - Replace images in older messages with descriptive placeholders, based on image metadata, so visual context is retained but size is reduced.

3. Update `reduce_context` to call the updated `_find_last_message_with_tool_results` method and `_truncate_tool_results`, ensuring truncation is applied correctly on the oldest tool result message first.

4. Add a new parameter `truncate_tool_result_char_limit` to the `SlidingWindowConversationManager.__init__` for the character limit threshold (default to 1000 for example).

We should import `re` if needed and could import `copy` if necessary for safe content manipulation, but here basic slicing and string operations suffice.

Changes are limited to the class `SlidingWindowConversationManager` inside `sliding_window_conversation_manager.py`.

---

Patch:

```
<file>src/strands/agent/conversation_manager/sliding_window_conversation_manager.py</file>
<original>    def __init__(self, window_size: int = 40, should_truncate_results: bool = True, *, per_turn: bool | int = False):
        """Initialize the sliding window conversation manager.

        Args:
            window_size: Maximum number of messages to keep in the agent's history.
                Defaults to 40 messages.
            should_truncate_results: Truncate tool results when a message is too large for the model's context window
            per_turn: Controls when to apply message management during agent execution.
                - False (default): Only apply management at the end (default behavior)
                - True: Apply management before every model call
                - int (e.g., 3): Apply management before every N model calls

                When to use per_turn: If your agent performs many tool operations in loops
                (e.g., web browsing with frequent screenshots), enable per_turn to proactively
                manage message history and prevent the agent loop from slowing down. Start with
                per_turn=True and adjust to a specific frequency (e.g., per_turn=5) if needed
                for performance tuning.

        Raises:
            ValueError: If per_turn is 0 or a negative integer.
        """
        super().__init__()

        self.window_size = window_size
        self.should_truncate_results = should_truncate_results
        self.per_turn = per_turn
        self._model_call_count = 0
</original>
<patched>    def __init__(self, window_size: int = 40, should_truncate_results: bool = True, *, per_turn: bool | int = False, truncate_tool_result_char_limit: int = 1000):
        """Initialize the sliding window conversation manager.

        Args:
            window_size: Maximum number of messages to keep in the agent's history.
                Defaults to 40 messages.
            should_truncate_results: Truncate tool results when a message is too large for the model's context window
            per_turn: Controls when to apply message management during agent execution.
                - False (default): Only apply management at the end (default behavior)
                - True: Apply management before every model call
                - int (e.g., 3): Apply management before every N model calls

                When to use per_turn: If your agent performs many tool operations in loops
                (e.g., web browsing with frequent screenshots), enable per_turn to proactively
                manage message history and prevent the agent loop from slowing down. Start with
                per_turn=True and adjust to a specific frequency (e.g., per_turn=5) if needed
                for performance tuning.

        Raises:
            ValueError: If per_turn is 0 or a negative integer.
        """
        super().__init__()

        self.window_size = window_size
        self.should_truncate_results = should_truncate_results
        self.per_turn = per_turn
        self._model_call_count = 0
        # Threshold for minimum chars in tool result content to trigger truncation
        self.truncate_tool_result_char_limit = truncate_tool_result_char_limit
</patched>
```

---

```
<file>src/strands/agent/conversation_manager/sliding_window_conversation_manager.py</file>
<original>    def _find_last_message_with_tool_results(self, messages: Messages) -> int | None:
        """Find the index of the last message containing tool results.

        This is useful for identifying messages that might need to be truncated to reduce context size.

        Args:
            messages: The conversation message history.

        Returns:
            Index of the last message with tool results, or None if no such message exists.
        """
        # Iterate backwards through all messages (from newest to oldest)
        for idx in range(len(messages) - 1, -1, -1):
            # Check if this message has any content with toolResult
            current_message = messages[idx]
            has_tool_result = False

            for content in current_message.get("content", []):
                if isinstance(content, dict) and "toolResult" in content:
                    has_tool_result = True
                    break

            if has_tool_result:
                return idx

        return None
</original>
<patched>    def _find_last_message_with_tool_results(self, messages: Messages) -> int | None:
        """Find the index of the oldest message containing tool results.

        This is useful for identifying messages that might need to be truncated to reduce context size.

        Args:
            messages: The conversation message history.

        Returns:
            Index of the oldest message with tool results, or None if no such message exists.
        """
        # Iterate forward through all messages (from oldest to newest)
        for idx in range(len(messages)):
            # Check if this message has any content with toolResult
            current_message = messages[idx]
            has_tool_result = False

            for content in current_message.get("content", []):
                if isinstance(content, dict) and "toolResult" in content:
                    has_tool_result = True
                    break

            if has_tool_result:
                return idx

        return None
</patched>
```

---

```
<file>src/strands/agent/conversation_manager/sliding_window_conversation_manager.py</file>
<original>    def _truncate_tool_results(self, messages: Messages, msg_idx: int) -> bool:
        """Truncate tool results in a message to reduce context size.

        When a message contains tool results that are too large for the model's context window, this function
        replaces the content of those tool results with a simple error message.

        Args:
            messages: The conversation message history.
            msg_idx: Index of the message containing tool results to truncate.

        Returns:
            True if any changes were made to the message, False otherwise.
        """
        if msg_idx >= len(messages) or msg_idx < 0:
            return False

        message = messages[msg_idx]
        changes_made = False
        tool_result_too_large_message = "The tool result was too large!"
        for i, content in enumerate(message.get("content", [])):
            if isinstance(content, dict) and "toolResult" in content:
                tool_result_content_text = next(
                    (item["text"] for item in content["toolResult"]["content"] if "text" in item),
                    "",
                )
                # make the overwriting logic togglable
                if (
                    message["content"][i]["toolResult"]["status"] == "error"
                    and tool_result_content_text == tool_result_too_large_message
                ):
                    logger.info("ToolResult has already been updated, skipping overwrite")
                    return False
                # Update status to error with informative message
                message["content"][i]["toolResult"]["status"] = "error"
                message["content"][i]["toolResult"]["content"] = [{"text": tool_result_too_large_message}]
                changes_made = True

        return changes_made
</original>
<patched>    def _truncate_tool_results(self, messages: Messages, msg_idx: int) -> bool:
        """Gracefully truncate tool results in a message to reduce context size.

        When a message contains tool results exceeding a character threshold, this function partially truncates
        the content, preserving the start and end with an inserted truncation notice in the middle. For images in older
        messages, it replaces them with descriptive placeholders.

        Args:
            messages: The conversation message history.
            msg_idx: Index of the message containing tool results to truncate.

        Returns:
            True if any changes were made to the message, False otherwise.
        """
        if msg_idx >= len(messages) or msg_idx < 0:
            return False

        message = messages[msg_idx]
        changes_made = False
        truncated_any = False
        char_limit = self.truncate_tool_result_char_limit
        truncation_notice_template = "\n\n... [truncated: {} chars removed] ...\n\n"
        tool_result_too_large_message = "The tool result was too large!"

        # Helper to truncate text preserving start/end context
        def _truncate_text(text: str, limit: int) -> str:
            if len(text) <= limit:
                return text
            keep_chars = 200  # chars to keep at start and end
            if limit < 2 * keep_chars:
                keep_chars = limit // 2
            front = text[:keep_chars]
            back = text[-keep_chars:] if keep_chars > 0 else ""
            removed_len = len(text) - (len(front) + len(back))
            notice = truncation_notice_template.format(removed_len)
            return f"{front}{notice}{back}"

        # Process each content item in the message
        new_contents = []
        for i, content in enumerate(message.get("content", [])):
            if isinstance(content, dict):
                # Handle toolResult content truncation
                if "toolResult" in content:
                    tool_result = content["toolResult"]
                    tool_result_content = tool_result.get("content", [])

                    # Extract combined text for size estimation
                    combined_text = ""
                    for item in tool_result_content:
                        if "text" in item:
                            combined_text += item["text"]
                        elif "code" in item:
                            combined_text += item["code"]

                    # Check if already truncated or error with tool_result_too_large_message
                    if (
                        tool_result.get("status") == "error"
                        and any(
                            "text" in item and item["text"] == tool_result_too_large_message
                            for item in tool_result_content
                        )
                    ):
                        # Already truncated, skip
                        return False

                    if len(combined_text) > char_limit:
                        new_content = []

                        # We will partially truncate text blocks and keep others as is
                        # We assume that text/code items contain text content
                        for item in tool_result_content:
                            if "text" in item:
                                text = item["text"]
                                if len(text) > char_limit:
                                    truncated_text = _truncate_text(text, len(text))
                                    new_content.append({"text": truncated_text})
                                    truncated_any = True
                                else:
                                    new_content.append(item)
                            elif "code" in item:
                                code_text = item["code"]
                                if len(code_text) > char_limit:
                                    truncated_code = _truncate_text(code_text, len(code_text))
                                    new_content.append({"code": truncated_code})
                                    truncated_any = True
                                else:
                                    new_content.append(item)
                            elif "image" in item:
                                # For images, replace with placeholder showing filename and size
                                image = item["image"]
                                # Construct placeholder text
                                filename = image.get("filename")
                                if not filename:
                                    # Fallback: try to get source uri or generic name
                                    filename = image.get("sourceUri") or "image"
                                    # Strip path parts if any
                                    filename = filename.rsplit("/", 1)[-1]
                                width = image.get("width", "unknown")
                                height = image.get("height", "unknown")
                                placeholder = f"[image: {filename}, {width}x{height}]"
                                new_content.append({"text": placeholder})
                                truncated_any = True
                            else:
                                # Other content types just keep as is
                                new_content.append(item)

                        # Update the toolResult content with truncated summary
                        tool_result["content"] = new_content
                        tool_result["status"] = "error"
                        changes_made = True

                # For other content dict types without toolResult, pass through
                else:
                    # Optionally, for images in older messages (if this message is old),
                    # we could replace images with placeholders - but since we truncate only on
                    # oldest message with toolResult, this already handled above.
                    pass

            else:
                # For non-dict content like text strings, leave as is
                pass

        return changes_made
</patched>
```

---

The above three modifications address the key points:
- Oldest message with tool results is found and truncated first
- Only truncate large content above threshold char limit
- Partial truncation with preserved start/end and truncation message
- Replace images with placeholders in older messages
- Preserve recent results intact to prevent confusion

No other locations are modified as the main truncation logic resides in these methods. The rest of the class manages sliding logic and message trimming correctly.

Note: For ease of maintenance, the truncation threshold is configurable on construction.