The root cause of the issue is that the formatter flushes the accumulated content_blocks into a separate user message whenever it encounters a ToolResultBlock and content_blocks is not empty. This causes multiple ToolResultBlocks in the same Assistant message to be split into multiple user messages, which DeepSeek rejects.

To fix this, we should modify the flush condition when encountering a ToolResultBlock so that it only flushes content_blocks if we are not already processing (accumulating) a tool_result message. This can be done by changing the condition from `if content_blocks:` to `if content_blocks and not has_tool_result:`. This way, all subsequent ToolResultBlocks are merged into a single user message, matching DeepSeek's requirements.

This is a minimal change that preserves existing behavior for single tool_result blocks.

Here is the patch:

```
<file>src/agentscope/formatter/_anthropic_formatter.py</file>
<original>                elif isinstance(block, ToolResultBlock):
                    if content_blocks:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []

                    tool_result_content: list[dict] = []
                    output = block.output
                    if isinstance(output, str):
                        tool_result_content.append(
                            {"type": "text", "text": output},
                        )
                    else:
                        for out_block in output:
                            if isinstance(out_block, TextBlock):
                                tool_result_content.append(
                                    {"type": "text", "text": out_block.text},
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

                    content_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_content,
                        },
                    )
                    # Anthropic requires tool_result to be in a "user" message.
                    has_tool_result = True
</original>
<patched>                elif isinstance(block, ToolResultBlock):
                    if content_blocks and not has_tool_result:
                        role = "user" if has_tool_result else msg.role
                        messages.append(
                            {"role": role, "content": content_blocks},
                        )
                        content_blocks = []

                    tool_result_content: list[dict] = []
                    output = block.output
                    if isinstance(output, str):
                        tool_result_content.append(
                            {"type": "text", "text": output},
                        )
                    else:
                        for out_block in output:
                            if isinstance(out_block, TextBlock):
                                tool_result_content.append(
                                    {"type": "text", "text": out_block.text},
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

                    content_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_content,
                        },
                    )
                    # Anthropic requires tool_result to be in a "user" message.
                    has_tool_result = True
</patched>
```