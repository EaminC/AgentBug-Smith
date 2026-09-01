The issue centers around the requirement by Anthropic's extended thinking feature that the `thinking` or `redacted_thinking` content blocks in the last assistant message must be passed back byte-for-byte exactly as received from the API, without any modification. The bug arises because the message formatting in `_AnthropicFormatterBase` reformats or potentially drops these blocks if the signature is missing or altered. This causes the API to return a 500 error, as the server detects the `thinking` blocks have been modified.

The fix is to ensure these `thinking` and `redacted_thinking` blocks in the final assistant message are preserved exactly as received, including their signature fields and ordering. In the formatter, if such blocks don't have a signature, they are currently dropped to avoid sending invalid data. However, for the latest assistant message we must include them exactly as-is, even if that includes an empty or missing signature, because dropping or modifying them changes the message content and triggers the error. Therefore, the formatter must be able to handle and preserve these blocks exactly as they come in, potentially by passing through any raw blocks without alteration.

This means modifying the `_format_messages` method in `_AnthropicFormatterBase` so that:

- It detects when it is formatting the latest assistant message (e.g., last message in the list and role=='assistant'), and for that message it should preserve `thinking`/`redacted_thinking` blocks exactly as they are, including empty or missing signatures.
- For other messages and blocks, the existing stricter logic can remain.

If the formatter doesn't yet have this context (which it likely does not), we may need to adjust the AnthropicChatModel’s `_call_api` function to detect the latest assistant message and pass it differently or flag it to the formatter. Given that the formatter only receives the list of messages, and the last assistant message is last in the list, we can enhance the formatter to receive the raw blocks for the last assistant message untouched.

Since the formatter is complex with many block types, the safer approach here is:

- In `_AnthropicFormatterBase._format_messages`, when processing a message, check if it is the last assistant message in the list (by using index); if so, and if it contains any `thinking` or `redacted_thinking` blocks, preserve those blocks exactly as they appear in that message's content blocks, without dropping or altering signatures or fields.

- For all other messages and blocks, keep existing logic.

This minimal change will ensure the last assistant message’s `thinking` blocks remain exactly the same, preventing the server error.

---

# Patch:

```
<file>src/agentscope/formatter/_anthropic_formatter.py</file>
<original>    async def _format_messages(
        self,
        msgs: list[Msg],
    ) -> list[dict[str, Any]]:
        """Format message objects into Anthropic API format.

        Args:
            msgs (`list[Msg]`):
                The list of message objects to format.

        Returns:
            `list[dict[str, Any]]`:
                The formatted messages as a list of dictionaries.

        .. note:: Anthropic suggests always passing all previous thinking
         blocks back to the API in subsequent calls to maintain reasoning
         continuity. For more details, please refer to
         `Anthropic's documentation
         <https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#preserving-thinking-blocks>`_.
        """
        self.assert_list_of_msgs(msgs)

        messages: list[dict] = []
        for msg in msgs:  # pylint: disable=too-many-nested-blocks
            content_blocks: list = []
            has_tool_result = False

            for block in msg.get_content_blocks():
                if (
                    has_tool_result
                    and content_blocks
                    and not isinstance(
                        block,
                        ToolResultBlock,
                    )
                ):
                    messages.append(
                        {"role": "user", "content": content_blocks},
                    )
                    content_blocks = []
                    has_tool_result = False

                if isinstance(block, TextBlock):
                    # Anthropic rejects empty text blocks with a 400
                    # ("text blocks must be non-empty"). Empty TextBlocks
                    # occur after a tool-call-only assistant turn whose
                    # streamed text is empty, so drop them here.
                    if block.text:
                        content_blocks.append(
                            {"type": "text", "text": block.text},
                        )

                elif isinstance(block, ThinkingBlock):
                    # Anthropic rejects thinking blocks without a valid
                    # signature ("Invalid `signature` in `thinking` block").
                    # ThinkingBlocks from other providers (OpenAI, DeepSeek,
                    # ...) carry no signature, so drop them instead of
                    # forwarding an empty one.
                    signature = getattr(block, "signature", None)
                    if signature:
                        content_blocks.append(
                            {
                                "type": "thinking",
                                "thinking": block.thinking,
                                "signature": signature,
                            },
                        )
                    else:
                        logger.debug(
                            "Dropping ThinkingBlock without signature; "
                            "Anthropic requires a valid signature.",
                        )

                elif isinstance(block, HintBlock):
                    if content_blocks:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []
                        has_tool_result = False

                    if isinstance(block.hint, str):
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": block.hint},
                                ],
                            },
                        )
                    else:
                        hint_parts: list[dict] = []
                        for sub in block.hint:
                            if isinstance(sub, TextBlock):
                                hint_parts.append(
                                    {"type": "text", "text": sub.text},
                                )
                            elif isinstance(sub, DataBlock):
                                formatted_sub = (
                                    self._format_anthropic_data_block(sub)
                                )
                                if formatted_sub:
                                    hint_parts.append(formatted_sub)
                        if hint_parts:
                            messages.append(
                                {"role": "user", "content": hint_parts},
                            )

                elif isinstance(block, DataBlock):
                    formatted_block = self._format_anthropic_data_block(block)
                    if formatted_block:
                        content_blocks.append(formatted_block)

                elif isinstance(block, ToolCallBlock):
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            # Anthropic API expects input as a dict, not a
                            # JSON string. Use the repair helper so a
                            # truncated input (from interrupted streaming or
                            # context compression) degrades to {} instead of
                            # raising JSONDecodeError.
                            "input": _json_loads_with_repair(
                                block.input or "{}",
                            ),
                        },
                    )

                elif isinstance(block, ToolResultBlock):
                    # Only flush when we have non-tool-result content
                    # (i.e. the preceding assistant turn). Once
                    # `has_tool_result` is True we are already accumulating
                    # tool_results into the current user message, so we must
                    # NOT flush on each additional ToolResultBlock — doing so
                    # would split parallel results into separate user messages
                    # which strict endpoints (e.g. DeepSeek) reject with 400.
                    if content_blocks and not has_tool_result:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []

                    tool_result_content: list[dict] = []
                    output = block.output
                    if isinstance(output, str):
                        if output:
                            tool_result_content.append(
                                {"type": "text", "text": output},
                            )
                    else:
                        for out_block in output:
                            if isinstance(out_block, TextBlock):
                                # Skip empty text — Anthropic rejects
                                # {"type": "text", "text": ""}.
                                if out_block.text:
                                    tool_result_content.append(
                                        {
                                            "type": "text",
                                            "text": out_block.text,
                                        },
                                    )
                            elif isinstance(out_block, DataBlock):
                                fmt_block = self._format_anthropic_data_block(
                                    out_block,
                                )
                                if fmt_block:
                                    tool_result_content.append(fmt_block)
                                else:
                                    source = out_block.source
                                    main_type = source.media_type.split("/")[0]
                                    if isinstance(source, URLSource):
                                        fallback = (
                                            f"[{main_type} file returned, "
                                            f"URL: {source.url}]"
                                        )
                                    else:
                                        fallback = (
                                            f"[{main_type} file returned, "
                                            f"type: {source.media_type}]"
                                        )
                                    tool_result_content.append(
                                        {"type": "text", "text": fallback},
                                    )

                    # Anthropic rejects a tool_result whose content list is
                    # empty. If every output block was an empty text (or the
                    # output was an empty string), fall back to a placeholder
                    # so the tool_result remains valid.
                    if not tool_result_content:
                        tool_result_content.append(
                            {"type": "text", "text": "(empty tool output)"},
                        )

                    content_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_content,
                        },
                    )
                    # Anthropic requires tool_result to be in a "user" message.
                    has_tool_result = True

                else:
                    logger.warning(
                        "Unsupported block type %s in the message, skipped.",
                        type(block),
                    )

            if content_blocks:
                # Anthropic requires `tool_result` blocks to be in a `user`
                # message regardless of the containing Msg's role.
                role = "user" if has_tool_result else msg.role
                messages.append(
                    {
                        "role": role,
                        "content": content_blocks,
                    },
                )

        return messages
</original>
<patched>    async def _format_messages(
        self,
        msgs: list[Msg],
    ) -> list[dict[str, Any]]:
        """Format message objects into Anthropic API format.

        Args:
            msgs (`list[Msg]`):
                The list of message objects to format.

        Returns:
            `list[dict[str, Any]]`:
                The formatted messages as a list of dictionaries.

        .. note:: Anthropic suggests always passing all previous thinking
         blocks back to the API in subsequent calls to maintain reasoning
         continuity. For more details, please refer to
         `Anthropic's documentation
         <https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking#preserving-thinking-blocks>`_.
        """
        self.assert_list_of_msgs(msgs)

        messages: list[dict] = []
        last_msg_index = len(msgs) - 1

        for i, msg in enumerate(msgs):  # pylint: disable=too-many-nested-blocks
            content_blocks: list = []
            has_tool_result = False

            # For the last assistant message, preserve thinking blocks exactly
            preserve_thinking_blocks = (
                i == last_msg_index and msg.role == "assistant"
            )

            for block in msg.get_content_blocks():
                if (
                    has_tool_result
                    and content_blocks
                    and not isinstance(
                        block,
                        ToolResultBlock,
                    )
                ):
                    messages.append(
                        {"role": "user", "content": content_blocks},
                    )
                    content_blocks = []
                    has_tool_result = False

                if isinstance(block, TextBlock):
                    # Anthropic rejects empty text blocks with a 400
                    # ("text blocks must be non-empty"). Empty TextBlocks
                    # occur after a tool-call-only assistant turn whose
                    # streamed text is empty, so drop them here.
                    if block.text:
                        content_blocks.append(
                            {"type": "text", "text": block.text},
                        )

                elif isinstance(block, ThinkingBlock):
                    signature = getattr(block, "signature", None)
                    if preserve_thinking_blocks:
                        # Preserve thinking blocks exactly as received,
                        # including those without signatures.
                        content_blocks.append(
                            {
                                "type": "thinking",
                                "thinking": block.thinking,
                                "signature": signature or "",
                            },
                        )
                    else:
                        # Anthropic rejects thinking blocks without a valid
                        # signature ("Invalid `signature` in `thinking` block").
                        # ThinkingBlocks from other providers (OpenAI, DeepSeek,
                        # ...) carry no signature, so drop them instead of
                        # forwarding an empty one.
                        if signature:
                            content_blocks.append(
                                {
                                    "type": "thinking",
                                    "thinking": block.thinking,
                                    "signature": signature,
                                },
                            )
                        else:
                            logger.debug(
                                "Dropping ThinkingBlock without signature; "
                                "Anthropic requires a valid signature.",
                            )

                elif isinstance(block, HintBlock):
                    if content_blocks:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []
                        has_tool_result = False

                    if isinstance(block.hint, str):
                        messages.append(
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": block.hint},
                                ],
                            },
                        )
                    else:
                        hint_parts: list[dict] = []
                        for sub in block.hint:
                            if isinstance(sub, TextBlock):
                                hint_parts.append(
                                    {"type": "text", "text": sub.text},
                                )
                            elif isinstance(sub, DataBlock):
                                formatted_sub = (
                                    self._format_anthropic_data_block(sub)
                                )
                                if formatted_sub:
                                    hint_parts.append(formatted_sub)
                        if hint_parts:
                            messages.append(
                                {"role": "user", "content": hint_parts},
                            )

                elif isinstance(block, DataBlock):
                    formatted_block = self._format_anthropic_data_block(block)
                    if formatted_block:
                        content_blocks.append(formatted_block)

                elif isinstance(block, ToolCallBlock):
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            # Anthropic API expects input as a dict, not a
                            # JSON string. Use the repair helper so a
                            # truncated input (from interrupted streaming or
                            # context compression) degrades to {} instead of
                            # raising JSONDecodeError.
                            "input": _json_loads_with_repair(
                                block.input or "{}",
                            ),
                        },
                    )

                elif isinstance(block, ToolResultBlock):
                    # Only flush when we have non-tool-result content
                    # (i.e. the preceding assistant turn). Once
                    # `has_tool_result` is True we are already accumulating
                    # tool_results into the current user message, so we must
                    # NOT flush on each additional ToolResultBlock — doing so
                    # would split parallel results into separate user messages
                    # which strict endpoints (e.g. DeepSeek) reject with 400.
                    if content_blocks and not has_tool_result:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []

                    tool_result_content: list[dict] = []
                    output = block.output
                    if isinstance(output, str):
                        if output:
                            tool_result_content.append(
                                {"type": "text", "text": output},
                            )
                    else:
                        for out_block in output:
                            if isinstance(out_block, TextBlock):
                                # Skip empty text — Anthropic rejects
                                # {"type": "text", "text": ""}.
                                if out_block.text:
                                    tool_result_content.append(
                                        {
                                            "type": "text",
                                            "text": out_block.text,
                                        },
                                    )
                            elif isinstance(out_block, DataBlock):
                                fmt_block = self._format_anthropic_data_block(
                                    out_block,
                                )
                                if fmt_block:
                                    tool_result_content.append(fmt_block)
                                else:
                                    source = out_block.source
                                    main_type = source.media_type.split("/")[0]
                                    if isinstance(source, URLSource):
                                        fallback = (
                                            f"[{main_type} file returned, "
                                            f"URL: {source.url}]"
                                        )
                                    else:
                                        fallback = (
                                            f"[{main_type} file returned, "
                                            f"type: {source.media_type}]"
                                        )
                                    tool_result_content.append(
                                        {"type": "text", "text": fallback},
                                    )

                    # Anthropic rejects a tool_result whose content list is
                    # empty. If every output block was an empty text (or the
                    # output was an empty string), fall back to a placeholder
                    # so the tool_result remains valid.
                    if not tool_result_content:
                        tool_result_content.append(
                            {"type": "text", "text": "(empty tool output)"},
                        )

                    content_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_content,
                        },
                    )
                    # Anthropic requires tool_result to be in a "user" message.
                    has_tool_result = True

                else:
                    logger.warning(
                        "Unsupported block type %s in the message, skipped.",
                        type(block),
                    )

            if content_blocks:
                # Anthropic requires `tool_result` blocks to be in a `user`
                # message regardless of the containing Msg's role.
                role = "user" if has_tool_result else msg.role
                messages.append(
                    {
                        "role": role,
                        "content": content_blocks,
                    },
                )

        return messages
</patched>
</file>
```

Explanation:

- Added detection of the last assistant message in `_format_messages`.
- For that last assistant message, when processing `ThinkingBlock`s, preserve the block exactly as received including signature and even empty or missing signature (set to empty string), instead of dropping them.
- This ensures that the exact byte-for-byte content of the last assistant message's thinking blocks is preserved and replayed to the API unmodified, thus preventing the 500 error.
- For all other messages/thinking blocks, keep current behavior (drop if no signature).
- This minimal fix prevents inadvertent modification or dropping of required thinking blocks in the latest assistant message.

No other changes are necessary here based on the supplied code. This focuses on the root cause: the message formatting stage.