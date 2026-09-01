Reasoning:

The issue arises because toolUse and toolResult events that are logically paired are stored as separate messages and can potentially be split apart due to the pagination limits (like default limit 100). This breaks the context during agent hydration because toolResult messages may appear without their preceding toolUse messages, causing validation errors.

Current fix in _fix_broken_tool_use only addresses the case of orphaned toolUse messages without matching toolResults. However, the reverse case - orphaned toolResult messages without preceding toolUse messages - also needs fixing as per the issue description.

To fix this:

1. We should enhance the _fix_broken_tool_use method in RepositorySessionManager to also fix orphaned toolResult messages by inserting or generating dummy toolUse messages before such toolResult messages.

2. We will create a new helper function similar to generate_missing_tool_result_content (already defined) that generates dummy toolUse content blocks for missing toolUse events.

3. Then in _fix_broken_tool_use, for each message, also check if a toolResult exists orphaned (i.e., previous message missing corresponding toolUse messages). If so, generate dummy toolUse blocks to prepend.

4. This will ensure that toolUse & toolResult pairs are always consistent, even when message boundary cuts occur.

Note: We do not override the list_messages method or others because the key fix should happen in the session hydration step where we fix these broken message histories after reading them.

Patch follows:


# modification 1: add generate_missing_tool_use_content helper in strands/tools/_tool_helpers.py

```
<file>src/strands/tools/_tool_helpers.py</file>
<original>19 def generate_missing_tool_result_content(tool_use_ids: list[str]) -> list[ContentBlock]:
20     """Generate ToolResult content blocks for orphaned ToolUse message."""
21     return [
22         {
23             "toolResult": {
24                 "toolUseId": tool_use_id,
25                 "status": "error",
26                 "content": [{"text": "Tool was interrupted."}],
27             }
28         }
29         for tool_use_id in tool_use_ids
30     ]
</original>
<patched>19 def generate_missing_tool_result_content(tool_use_ids: list[str]) -> list[ContentBlock]:
20     """Generate ToolResult content blocks for orphaned ToolUse message."""
21     return [
22         {
23             "toolResult": {
24                 "toolUseId": tool_use_id,
25                 "status": "error",
26                 "content": [{"text": "Tool was interrupted."}],
27             }
28         }
29         for tool_use_id in tool_use_ids
30     ]
31
32 def generate_missing_tool_use_content(tool_result_ids: list[str]) -> list[ContentBlock]:
33     """Generate ToolUse content blocks for orphaned ToolResult message."""
34     return [
35         {
36             "toolUse": {
37                 "toolUseId": tool_result_id,
38                 "tool": "unknown",
39                 "parameters": [],
40             }
41         }
42         for tool_result_id in tool_result_ids
43     ]
</patched>
```

# modification 2: enhance _fix_broken_tool_use in RepositorySessionManager to fix orphaned toolResult messages

```
<file>src/strands/session/repository_session_manager.py</file>
<original>167     def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
168         """Add tool_result after orphaned tool_use messages.
169 
170         Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
171         This method retroactively fixes that issue by adding a tool_result outside of session management. After 1.15.0,
172         this bug is no longer present.
173         """
174         for index, message in enumerate(messages):
175             # Check all but the latest message in the messages array
176             # The latest message being orphaned is handled in the agent class
177             if index + 1 < len(messages):
178                 if any("toolUse" in content for content in message["content"]):
179                     tool_use_ids = [
180                         content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
181                     ]
182 
183                     # Check if there are more messages after the current toolUse message
184                     tool_result_ids = [
185                         content["toolResult"]["toolUseId"]
186                         for content in messages[index + 1]["content"]
187                         if "toolResult" in content
188                     ]
189 
190                     missing_tool_use_ids = list(set(tool_use_ids) - set(tool_result_ids))
191                     # If there area missing tool use ids, that means the messages history is broken
192                     if missing_tool_use_ids:
193                         logger.warning(
194                             "Session message history has an orphaned toolUse with no toolResult. "
195                             "Adding toolResult content blocks to create valid conversation."
196                         )
197                         # Create the missing toolResult content blocks
198                         missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)
199 
200                         if tool_result_ids:
201                             # If there were any toolResult ids, that means only some of the content blocks are missing
202                             messages[index + 1]["content"].extend(missing_content_blocks)
203                         else:
204                             # The message following the toolUse was not a toolResult, so lets insert it
205                             messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
206         return messages
</original>
<patched>167     def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
168         """Add tool_result after orphaned tool_use messages.
169 
170         Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
171         This method retroactively fixes that issue by adding a tool_result outside of session management. After 1.15.0,
172         this bug is no longer present.
173 
174         This enhanced version also fixes orphaned toolResult messages by inserting missing toolUse messages.
175         """
176         from strands.tools._tool_helpers import generate_missing_tool_result_content, generate_missing_tool_use_content
177
178         index = 0
179         while index < len(messages):
180             message = messages[index]
181             # Fix orphaned toolUse messages missing toolResult (existing logic)
182             if index + 1 < len(messages):
183                 if any("toolUse" in content for content in message["content"]):
184                     tool_use_ids = [
185                         content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
186                     ]
187 
188                     # Check if there are more messages after the current toolUse message
189                     tool_result_ids = [
190                         content["toolResult"]["toolUseId"]
191                         for content in messages[index + 1]["content"]
192                         if "toolResult" in content
193                     ]
194 
195                     missing_tool_result_ids = list(set(tool_use_ids) - set(tool_result_ids))
196                     # If there are missing tool_result ids, fix by adding them
197                     if missing_tool_result_ids:
198                         logger.warning(
199                             "Session message history has an orphaned toolUse with no toolResult. "
200                             "Adding toolResult content blocks to create valid conversation."
201                         )
202                         missing_content_blocks = generate_missing_tool_result_content(missing_tool_result_ids)
203 
204                         if tool_result_ids:
205                             messages[index + 1]["content"].extend(missing_content_blocks)
206                         else:
207                             messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
208                         # After fix, continue next iteration on updated messages
209                         index += 1
210                         continue
211
212             # Fix orphaned toolResult messages missing preceding toolUse messages
213             # Check current message for toolResult blocks
214             if any("toolResult" in content for content in message["content"]):
215                 tool_result_ids = [
216                     content["toolResult"]["toolUseId"] for content in message["content"] if "toolResult" in content
217                 ]
218                 # Look at previous message if any
219                 prev_message = messages[index - 1] if index > 0 else None
220                 prev_tool_use_ids = []
221                 if prev_message:
222                     prev_tool_use_ids = [
223                         content["toolUse"]["toolUseId"] for content in prev_message["content"] if "toolUse" in content
224                     ]
225                 missing_tool_use_ids = list(set(tool_result_ids) - set(prev_tool_use_ids))
226                 if missing_tool_use_ids:
227                     logger.warning(
228                         "Session message history has an orphaned toolResult with no preceding toolUse. "
229                         "Adding toolUse content blocks to create valid conversation."
230                     )
231                     missing_tool_use_contents = generate_missing_tool_use_content(missing_tool_use_ids)
232                     # Insert a dummy message before current message containing missing toolUse contents
233                     messages.insert(index, {"role": "user", "content": missing_tool_use_contents})
234                     # Increment index to skip over the inserted message next loop
235                     index += 1
236                     continue
237
238             index += 1
239 
240         return messages
</patched>
```
