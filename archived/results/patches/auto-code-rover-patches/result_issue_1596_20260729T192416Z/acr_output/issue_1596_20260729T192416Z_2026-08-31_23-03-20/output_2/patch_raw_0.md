The issue is that in the main reasoning-acting loop inside the `_reply_impl` method, the loop prematurely breaks whenever the reasoning step returns a message that has no tool_use blocks. Originally, the assumption is that if no tool_use blocks are found, it must be a text block and hence the reasoning is done. However, certain models with extended thinking return only thinking blocks and no tool_use or text blocks. In such cases, the current logic breaks the loop and returns a message without user-visible content, which is undesirable.

The fix is to change the break condition to also check for the presence of text content blocks. Only when there is no tool_use block and at least one text block present, the loop should break and return the message. Otherwise, when there are only thinking blocks, it should continue the loop, allowing the model to produce actual text or tool calls in subsequent iterations.

This requires modifying the condition where the `_reply_impl` receives a message from the reasoning step and decides whether to break out of the loop.

Here is the patch to fix the issue:

```
<file>src/agentscope/agent/_agent.py</file>
<original>
775                             yield evt
776                             return
...
</original>
<patched>
775                             # Only break if there is actual text content to show the user,
776                             # otherwise continue the loop for more reasoning
777                             if evt.has_content_blocks("text") or evt.has_content_blocks("tool_use"):
778                                 yield evt
779                                 return
</patched>
```

Explanation:
- After receiving the Msg event (evt) from the reasoning step, check if it has either text or tool_use blocks.
- If yes, yield the message and break the loop (return).
- Otherwise, continue the loop to allow more reasoning loops if only thinking blocks are present.

This minimal change addresses the problem described without affecting other functionality of the loop.

# Final patch below.

```
<file>src/agentscope/agent/_agent.py</file>
<original>
775                             yield evt
776                             return
</original>
<patched>
775                             # Only break if there is actual text content to show the user,
776                             # otherwise continue the loop for more reasoning
777                             if evt.has_content_blocks("text") or evt.has_content_blocks("tool_use"):
778                                 yield evt
779                                 return
</patched>
```