The root cause is that the AnthropicChatFormatter flushes (emits) content_blocks to messages whenever there are any content_blocks before processing a ToolResultBlock. This leads to multiple "user" messages when there are multiple tool_result blocks in a single assistant message, which DeepSeek rejects. The fix is to modify the flushing condition so that the flush happens only if content_blocks exist and we are not already handling a tool_result block (i.e., when has_tool_result is False). This way, multiple tool_result blocks can be merged into one user message as DeepSeek expects.

This minimal change preserves existing behavior for single tool_result or when no tool_results are present but merges multiple tool_results into one user message.

Here is the patch for the relevant code snippet in src/agentscope/formatter/_anthropic_formatter.py:

```
<file>src/agentscope/formatter/_anthropic_formatter.py</file>
<original>
153                 elif isinstance(block, ToolResultBlock):
154                     if content_blocks:
155                         role = "user" if has_tool_result else msg.role
156                         messages.append(
157                             {"role": role, "content": content_blocks},
158                         )
159                         content_blocks = []
160 
161                     tool_result_content: list[dict] = []
162                     output = block.output
163                     if isinstance(output, str):
164                         tool_result_content.append(
165                             {"type": "text", "text": output},
166                         )
167                     else:
168                         for out_block in output:
169                             if isinstance(out_block, TextBlock):
170                                 tool_result_content.append(
171                                     {"type": "text", "text": out_block.text},
172                                 )
173                             elif isinstance(out_block, DataBlock):
174                                 fmt_block = self._format_anthropic_data_block(
175                                     out_block,
176                                 )
177                                 if fmt_block:
178                                     tool_result_content.append(fmt_block)
179                                 else:
180                                     source = out_block.source
181                                     main_type = source.media_type.split("/")[0]
182                                     if isinstance(source, URLSource):
183                                         fallback = (
184                                             f"[{main_type} file returned, "
185                                             f"URL: {source.url}]"
186                                         )
187                                     else:
188                                         fallback = (
189                                             f"[{main_type} file returned, "
190                                             f"type: {source.media_type}]"
191                                         )
192                                     tool_result_content.append(
193                                         {"type": "text", "text": fallback},
194                                     )
195 
196                     content_blocks.append(
197                         {
198                             "type": "tool_result",
199                             "tool_use_id": block.id,
200                             "content": tool_result_content,
201                         },
202                     )
203                     # Anthropic requires tool_result to be in a "user" message.
204                     has_tool_result = True
</original>
<patched>
153                 elif isinstance(block, ToolResultBlock):
154                     if content_blocks and not has_tool_result:
155                         role = "user" if has_tool_result else msg.role
156                         messages.append(
157                             {"role": role, "content": content_blocks},
158                         )
159                         content_blocks = []
160 
161                     tool_result_content: list[dict] = []
162                     output = block.output
163                     if isinstance(output, str):
164                         tool_result_content.append(
165                             {"type": "text", "text": output},
166                         )
167                     else:
168                         for out_block in output:
169                             if isinstance(out_block, TextBlock):
170                                 tool_result_content.append(
171                                     {"type": "text", "text": out_block.text},
172                                 )
173                             elif isinstance(out_block, DataBlock):
174                                 fmt_block = self._format_anthropic_data_block(
175                                     out_block,
176                                 )
177                                 if fmt_block:
178                                     tool_result_content.append(fmt_block)
179                                 else:
180                                     source = out_block.source
181                                     main_type = source.media_type.split("/")[0]
182                                     if isinstance(source, URLSource):
183                                         fallback = (
184                                             f"[{main_type} file returned, "
185                                             f"URL: {source.url}]"
186                                         )
187                                     else:
188                                         fallback = (
189                                             f"[{main_type} file returned, "
190                                             f"type: {source.media_type}]"
191                                         )
192                                     tool_result_content.append(
193                                         {"type": "text", "text": fallback},
194                                     )
195 
196                     content_blocks.append(
197                         {
198                             "type": "tool_result",
199                             "tool_use_id": block.id,
200                             "content": tool_result_content,
201                         },
202                     )
203                     # Anthropic requires tool_result to be in a "user" message.
204                     has_tool_result = True
</patched>
```