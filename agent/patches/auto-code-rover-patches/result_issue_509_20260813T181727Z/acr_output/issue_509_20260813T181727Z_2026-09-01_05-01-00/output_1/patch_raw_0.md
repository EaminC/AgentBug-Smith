Reasoning:
The user wants to reduce the number of messages during the Agent loop execution because the message accumulation slows down the agent, especially when many tools are used. The user tried to call `apply_management` of `conversation_manager` in an AfterInvocation event hook, but it didn't work.

Looking at the agent loop in `src/strands/experimental/bidi/agent/loop.py`, it is clear that the loop is continuously receiving streaming events and appending messages when suitable. To manage the number of messages during the ongoing execution, it makes sense to call the `conversation_manager.apply_management(agent)` method right after appending messages, for example, after receiving the final transcript event (where messages are added) and after appending tool messages. This ensures that message pruning is applied continuously during the loop, not only after the entire invocation finishes.

Therefore, I will add calls to `self._agent.conversation_manager.apply_management(self._agent)` after:

- appending messages for a final transcript event inside `_run_model`
- appending tool use and tool result messages inside `_run_tool`

These minimal changes integrate conversation management dynamics into the ongoing loop execution and should evade message bloat and speedup the agent.

---

Patch:

```
<file>src/strands/experimental/bidi/agent/loop.py</file>
<original>                if isinstance(event, BidiTranscriptStreamEvent):
                    if event["is_final"]:
                        message: Message = {"role": event["role"], "content": [{"text": event["text"]}]}
                        await self._agent._append_messages(message)
</original>
<patched>                if isinstance(event, BidiTranscriptStreamEvent):
                    if event["is_final"]:
                        message: Message = {"role": event["role"], "content": [{"text": event["text"]}]}
                        await self._agent._append_messages(message)
                        # Apply conversation message management to prune messages dynamically
                        self._agent.conversation_manager.apply_management(self._agent)
</patched>
</file>

<file>src/strands/experimental/bidi/agent/loop.py</file>
<original>            await self._agent._append_messages(tool_use_message, tool_result_message)
 
            await self._event_queue.put(ToolResultMessageEvent(tool_result_message))
 
            # Check for stop_conversation before sending to model
            if tool_use["name"] == "stop_conversation":
                logger.info("tool_name=<%s> | conversation stop requested, skipping model send", tool_use["name"])
                connection_id = getattr(self._agent.model, "_connection_id", "unknown")
                await self._event_queue.put(
                    BidiConnectionCloseEvent(connection_id=connection_id, reason="user_request")
                )
                return  # Skip the model send
</original>
<patched>            await self._agent._append_messages(tool_use_message, tool_result_message)
            # Apply conversation message management to prune messages dynamically
            self._agent.conversation_manager.apply_management(self._agent)
 
            await self._event_queue.put(ToolResultMessageEvent(tool_result_message))
 
            # Check for stop_conversation before sending to model
            if tool_use["name"] == "stop_conversation":
                logger.info("tool_name=<%s> | conversation stop requested, skipping model send", tool_use["name"])
                connection_id = getattr(self._agent.model, "_connection_id", "unknown")
                await self._event_queue.put(
                    BidiConnectionCloseEvent(connection_id=connection_id, reason="user_request")
                )
                return  # Skip the model send
</patched>
</file>
```