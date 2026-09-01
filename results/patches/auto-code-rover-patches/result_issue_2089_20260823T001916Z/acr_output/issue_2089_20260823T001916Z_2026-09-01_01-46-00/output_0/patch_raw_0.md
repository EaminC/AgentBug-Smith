The issue is that when processing a `BidiTextInputEvent` in the `_BidiAgentLoop.send` method, the role of the message is hardcoded as `"user"`, ignoring the `role` attribute from the `BidiTextInputEvent` instance. This causes any injected input with a different role (like `"assistant"`) to lose that role information, which is not the intended behavior. The fix is straightforward: replace the hardcoded `"user"` string with `event.role` so the actual event role is respected and preserved.

No other changes are required since this point is the only place mentioned where the role is set in such a manner.

Here is the patch:


```
<file>strands-py/src/strands/experimental/bidi/agent/loop.py</file>
<original>        if isinstance(event, BidiTextInputEvent):
            message: Message = {"role": "user", "content": [{"text": event.text}]}
            await self._agent._append_messages(message)
</original>
<patched>        if isinstance(event, BidiTextInputEvent):
            message: Message = {"role": event.role, "content": [{"text": event.text}]}
            await self._agent._append_messages(message)
</patched>
```