```
<file>src/agentscope/agent/_agent.py</file>
<original>        # somewhere in the main reasoning-acting loop (exact function unknown):
        elif not msg_reasoning.has_content_blocks("tool_use"):
            # Exit the loop when no structured output is required (or
            # already satisfied) and only text response is generated
            msg_reasoning.metadata = structured_output
            reply_msg = msg_reasoning
            break
</original>
<patched>        # somewhere in the main reasoning-acting loop (exact function unknown):
        elif not msg_reasoning.has_content_blocks("tool_use"):
            # Only exit if there's actual text content for the user
            if msg_reasoning.has_content_blocks("text"):
                msg_reasoning.metadata = structured_output
                reply_msg = msg_reasoning
                break
            # else: only thinking blocks present, continue the loop
</patched>
```