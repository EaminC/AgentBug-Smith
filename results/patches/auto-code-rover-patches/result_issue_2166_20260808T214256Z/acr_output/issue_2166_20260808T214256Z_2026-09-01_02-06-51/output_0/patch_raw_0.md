The root cause of the duplicate `ToolResultStartEvent` events during the interruption of an external tool in the SUBMITTED state is that the `_close_unfinished_tool_calls` method currently excludes only the ALLOWED state from re-emitting the START event. However, for external tools, the lifecycle includes both ALLOWED and SUBMITTED states, both of which already emit the START event. As a result, when an interruption occurs while the tool call is in SUBMITTED state, `_close_unfinished_tool_calls` emits a redundant START event, causing duplication.

The fix is to update the condition in `_close_unfinished_tool_calls` to exclude both ALLOWED and SUBMITTED states from emitting the `ToolResultStartEvent`. This will ensure that exactly one START event is emitted per tool call — the one emitted when the tool call transitions into ALLOWED — and no extra START events upon interruption.

No other changes are needed because:
- The initial START event emission upon transition to ALLOWED is correct and desired.
- Other parts handling tool call states should remain unchanged to preserve functionality.

Below is the patch that fixes this issue:

```
<file>src/agentscope/agent/_agent.py</file>
<original>            # An ALLOWED call was already running, so its START was already
            # emitted — skip it here (checked before flipping to FINISHED).
            if call_block.state != ToolCallState.ALLOWED:
                yield ToolResultStartEvent(
                    reply_id=self.state.reply_id,
                    tool_call_id=last_msg.content[index].id,
                    tool_call_name=last_msg.content[index].name,
                )
</original>
<patched>            # An ALLOWED or SUBMITTED call was already running, so its START was already
            # emitted — skip it here (checked before flipping to FINISHED).
            if call_block.state not in (ToolCallState.ALLOWED, ToolCallState.SUBMITTED):
                yield ToolResultStartEvent(
                    reply_id=self.state.reply_id,
                    tool_call_id=last_msg.content[index].id,
                    tool_call_name=last_msg.content[index].name,
                )
</patched>
```