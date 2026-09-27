The problem lies in the error handling block of the `_process_tool_result` method in the `MCPClient` class. Currently, if the `result.isError` is True, the method raises a `ToolError` immediately, ignoring whether the `result.content` contains textual error details that might be valuable to return for further iteration or learning.

The fix should:
- Check if `result.isError` is True.
- If True, check if `result.content` has one or more items with a `text` attribute.
- If textual content is present, return that text (single string if one, list if multiple), instead of raising an error.
- Only if no textual content is present, raise the `ToolError`.
- Preserve the existing functionality for non-error results by extracting texts and returning them as before.

This preserves the spirit of returning error details to the caller while still raising exceptions for true error cases without useful content.

# modification 1
```
<file>dapr_agents/tool/mcp/client.py</file>
<original>        # Handle error result
        if hasattr(result, 'isError') and result.isError:
            error_message = "Unknown error"
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        error_message = content.text
                        break
            raise ToolError(f"MCP tool error: {error_message}")
        
        # Extract text content from result
        if hasattr(result, 'content') and result.content:
            text_contents = []
            for content in result.content:
                if hasattr(content, 'text'):
                    text_contents.append(content.text)
            
            # Return single string if only one content item
            if len(text_contents) == 1:
                return text_contents[0]
            elif text_contents:
                return text_contents
                
        # Fallback for unexpected formats
        return str(result)</original>
<patched>        # Handle error result, but if textual content is available, return it to enable iteration
        if hasattr(result, 'isError') and result.isError:
            # Extract text content if present
            if hasattr(result, 'content') and result.content:
                text_contents = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        text_contents.append(content.text)
                if len(text_contents) == 1:
                    return text_contents[0]
                elif text_contents:
                    return text_contents
            # No textual content found, raise error
            error_message = "Unknown error"
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        error_message = content.text
                        break
            raise ToolError(f"MCP tool error: {error_message}")
        
        # Extract text content from non-error result
        if hasattr(result, 'content') and result.content:
            text_contents = []
            for content in result.content:
                if hasattr(content, 'text'):
                    text_contents.append(content.text)
            
            # Return single string if only one content item
            if len(text_contents) == 1:
                return text_contents[0]
            elif text_contents:
                return text_contents
                
        # Fallback for unexpected formats
        return str(result)</patched>
```