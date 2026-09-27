Reasoning:

The root cause of the issue is that `OpenAIModel.format_request_tool_message()` currently returns the `content` field as a list of content blocks (an array), while many OpenAI-compatible endpoints (like Kimi K2.5) expect it as a single string. The fix is to always convert the multiple content blocks into one combined string. For JSON content blocks, their JSON representation should be used via `json.dumps()`. For text content, text should be appended directly. This concatenation should apply regardless of whether there is one content block or many.

The buggy code currently does this:
- Processes `tool_result["content"]` into formatted content blocks.
- If just one text block, returns `"content"` as that text string.
- Otherwise, returns `"content"` as the array of formatted content blocks.

This needs to be replaced by logic that always joins the text pieces into one string for `"content"`, addressing the compatibility issue.

The fix:
- Iterate over each content block in `tool_result["content"]`.
- For each block, if it has `"json"`, `json.dumps()` that into a string.
- If it has `"text"`, extract the text.
- Join these strings with newline separators (`"\n"`).
- Return the `"content"` dict key with the joined string.

No other part of the class or project apparently needs modification.

---

Patch:

```
<file>src/strands/models/openai.py</file>
<original>    def format_request_tool_message(cls, tool_result: ToolResult, **kwargs: Any) -> dict[str, Any]:
        """Format an OpenAI compatible tool message.

        Args:
            tool_result: Tool result collected from a tool execution.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            OpenAI compatible tool message.
        """
        contents = cast(
            list[ContentBlock],
            [
                {"text": json.dumps(content["json"])} if "json" in content else content
                for content in tool_result["content"]
            ],
        )

        formatted_contents = [cls.format_request_message_content(content) for content in contents]

        # If single text content, use string format for better model compatibility
        if len(formatted_contents) == 1 and formatted_contents[0].get("type") == "text":
            content: str | list[dict[str, Any]] = formatted_contents[0]["text"]
        else:
            content = formatted_contents

        return {
            "role": "tool",
            "tool_call_id": tool_result["toolUseId"],
            "content": content,
        }
</original>
<patched>    def format_request_tool_message(cls, tool_result: ToolResult, **kwargs: Any) -> dict[str, Any]:
        """Format an OpenAI compatible tool message.

        Args:
            tool_result: Tool result collected from a tool execution.
            **kwargs: Additional keyword arguments for future extensibility.

        Returns:
            OpenAI compatible tool message.
        """
        text_parts = []
        for content in tool_result["content"]:
            if "json" in content:
                text_parts.append(json.dumps(content["json"]))
            elif "text" in content:
                text_parts.append(content["text"])

        content_str = "\n".join(text_parts)

        return {
            "role": "tool",
            "tool_call_id": tool_result["toolUseId"],
            "content": content_str,
        }
</patched>
```
