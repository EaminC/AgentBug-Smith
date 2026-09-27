The root cause of the issue is that `OpenAIModel.format_request_tool_message()` returns the "content" field as an array of content blocks when the OpenAI API-compatible spec, especially for some implementations like Kimi K2.5, strictly requires the content as a single string. This causes hallucinations because those models fail to parse the array format.

The current implementation only returns a string if there is exactly one text block, otherwise returns the entire array, which breaks compatibility.

The fix is to always convert the tool message content to a single string, joining multiple content blocks with newline separators. For each content block:
- If the block holds JSON, it should be `json.dumps()` serialized.
- If it's a text block, extract the plain text.
- Ignore unsupported content types or raise? The current logic assumes only text/json, so follow that pattern.

This approach preserves all the informative content but guarantees output is always a string, which addresses compatibility while preserving information.

We will import `json` since we need `json.dumps()`.

Patch is limited to just modifying `format_request_tool_message`.

---

```
<file>src/strands/models/openai.py</file>
<original>189     def format_request_tool_message(cls, tool_result: ToolResult, **kwargs: Any) -> dict[str, Any]:
190         """Format an OpenAI compatible tool message.
191 
192         Args:
193             tool_result: Tool result collected from a tool execution.
194             **kwargs: Additional keyword arguments for future extensibility.
195 
196         Returns:
197             OpenAI compatible tool message.
198         """
199         contents = cast(
200             list[ContentBlock],
201             [
202                 {"text": json.dumps(content["json"])} if "json" in content else content
203                 for content in tool_result["content"]
204             ],
205         )
206 
207         formatted_contents = [cls.format_request_message_content(content) for content in contents]
208 
209         # If single text content, use string format for better model compatibility
210         if len(formatted_contents) == 1 and formatted_contents[0].get("type") == "text":
211             content: str | list[dict[str, Any]] = formatted_contents[0]["text"]
212         else:
213             content = formatted_contents
214 
215         return {
216             "role": "tool",
217             "tool_call_id": tool_result["toolUseId"],
218             "content": content,
219         }
</original>
<patched>189     def format_request_tool_message(cls, tool_result: ToolResult, **kwargs: Any) -> dict[str, Any]:
190         """Format an OpenAI compatible tool message.
191 
192         Args:
193             tool_result: Tool result collected from a tool execution.
194             **kwargs: Additional keyword arguments for future extensibility.
195 
196         Returns:
197             OpenAI compatible tool message.
198         """
199         # Compose text parts by serializing json content and extracting text
200         text_parts = []
201         for content in tool_result["content"]:
202             if "json" in content:
203                 text_parts.append(json.dumps(content["json"]))
204             elif "text" in content:
205                 text_parts.append(content["text"])
206 
207         combined_content = "\n".join(text_parts)
208 
209         return {
210             "role": "tool",
211             "tool_call_id": tool_result["toolUseId"],
212             "content": combined_content,
213         }
</patched>
```

Additionally, add `import json` at the top if not already imported.

```
<file>src/strands/models/openai.py</file>
<original>import base64
import mimetypes
...</original>
<patched>import base64
import json
import mimetypes
...</patched>
```