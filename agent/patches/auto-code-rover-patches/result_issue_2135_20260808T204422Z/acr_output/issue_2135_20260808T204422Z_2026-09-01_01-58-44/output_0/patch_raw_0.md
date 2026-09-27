Reasoning:
The root cause of the error is that the `thinking` and `redacted_thinking` content blocks in the latest assistant message must be preserved exactly as received from the Anthropic API when replaying messages back, including their order, content, and metadata (like signature). The Anthropic API raises a 500 error if these blocks are modified in any way.

Currently, the `_AnthropicFormatterBase._format_messages` method formats internal message objects into Anthropic API message format, but it can drop thinking blocks without signatures and reorder messages or blocks which might change the byte-to-byte makeup of messages that include `thinking` blocks.

To fix this, we need to ensure that if a message has any `thinking` or `redacted_thinking` blocks (especially the last assistant message), these blocks must be passed back exactly unmodified, preserving all metadata such as `signature`, and not filtering or altering them. If thinking blocks are present in the latest assistant message, they should be forwarded exactly as received, with no reserialization or omission.

Given the snippet, the best place to apply the minimal fix is within `_AnthropicFormatterBase._format_messages`: when reconstructing messages, if the input Msg already has thinking blocks with signatures, these blocks should be forwarded as-is to preserve exact bytes. We should avoid dropping or modifying these thinking blocks simply because the signature is missing or other checks, as that could break the required byte-for-byte preservation.

No changes to other parts of the code are needed if this formatter change is done properly to ensure the latest assistant messages with extended thinking have their thinking blocks passed intact.

---

Patch:

```
<file>src/agentscope/formatter/_anthropic_formatter.py</file>
<original>            for block in msg.get_content_blocks():
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
</original>
<patched>            for block in msg.get_content_blocks():
                # Preserve thinking blocks exactly if present (required for Anthropic extended thinking)
                if isinstance(block, ThinkingBlock):
                    signature = getattr(block, "signature", None)
                    if signature:
                        # Forward the thinking block exactly as is
                        content_blocks.append(
                            {
                                "type": "thinking",
                                "thinking": block.thinking,
                                "signature": signature,
                            },
                        )
                    else:
                        # Drop ThinkingBlocks without signature as Anthropic requires signature
                        logger.debug(
                            "Dropping ThinkingBlock without signature; "
                            "Anthropic requires a valid signature.",
                        )
                    continue

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
</patched>
```