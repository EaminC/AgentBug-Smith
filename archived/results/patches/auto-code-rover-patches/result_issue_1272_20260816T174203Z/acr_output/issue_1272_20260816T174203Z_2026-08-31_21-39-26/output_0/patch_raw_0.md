Reasoning:
The root issue is that when retrieving messages with pagination (e.g., limit=100), a toolResult message might be the last retrieved message, but its correlated toolUse message might be outside the retrieved range (the 101st event). This breaks validity because the conversation expects the toolUse before the toolResult.

To fix this, we must ensure that when paginating messages, if the first retrieved message is a toolResult message but its related toolUse message is missing (because it is outside the page), we must retrieve that toolUse message as well and prepend it, or if not found, create a dummy toolUse message that satisfies the requirement.

The best place to implement this logic is in the `list_messages` method of `S3SessionManager` where messages are read and returned.

Additionally, in the `_fix_broken_tool_use` method that currently fixes toolUse messages missing toolResult messages, we should complement it to also fix orphaned toolResult messages missing their toolUse messages.

To do this, we:

- In `list_messages`, after paginating and loading messages, check if the first message is a toolResult message with a toolUseId referencing a toolUse message outside the retrieved subset. If so, load or generate the missing toolUse message and prepend it.

- In `_fix_broken_tool_use`, add logic to handle orphaned toolResult messages by checking if the corresponding toolUse messages are missing before them, and prepend dummy toolUse content if necessary.

- To generate dummy toolUse content, add a new helper function similar to `generate_missing_tool_result_content`.

Now, implementing these patches accordingly.

---

# modification 1
Add helper function to generate dummy toolUse content in `src/strands/tools/_tool_helpers.py`.

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
32 def generate_missing_tool_use_content(tool_use_ids: list[str]) -> list[ContentBlock]:
33     """Generate ToolUse content blocks for orphaned ToolResult message."""
34     return [
35         {
36             "toolUse": {
37                 "toolUseId": tool_use_id,
38                 "tool": {"name": "UNKNOWN"},
39                 "content": [{"text": "Dummy toolUse to fix missing context"}],
40             }
41         }
42         for tool_use_id in tool_use_ids
43     ]
</patched>
```

---

# modification 2
Modify `RepositorySessionManager._fix_broken_tool_use` in `src/strands/session/repository_session_manager.py` to also fix orphaned toolResult messages missing toolUse messages.

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
168         """Add tool_result after orphaned tool_use messages and add tool_use before orphaned tool_result messages.
169 
170         Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
171         This method retroactively fixes that issue by adding a tool_result outside of session management. After 1.15.0,
172         this bug is no longer present.
173         """
174         for index, message in enumerate(messages):
175             # Check all but the latest message in the messages array
176             # The latest message being orphaned is handled in the agent class
177             if index + 1 < len(messages):
178                 # Fix orphaned toolUse missing toolResult (existing logic)
179                 if any("toolUse" in content for content in message["content"]):
180                     tool_use_ids = [
181                         content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
182                     ]
183 
184                     # Check if there are more messages after the current toolUse message
185                     tool_result_ids = [
186                         content["toolResult"]["toolUseId"]
187                         for content in messages[index + 1]["content"]
188                         if "toolResult" in content
189                     ]
190 
191                     missing_tool_use_ids = list(set(tool_use_ids) - set(tool_result_ids))
192                     # If there are missing tool use ids, that means the messages history is broken
193                     if missing_tool_use_ids:
194                         logger.warning(
195                             "Session message history has an orphaned toolUse with no toolResult. "
196                             "Adding toolResult content blocks to create valid conversation."
197                         )
198                         # Create the missing toolResult content blocks
199                         missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)
200 
201                         if tool_result_ids:
202                             # If there were any toolResult ids, that means only some of the content blocks are missing
203                             messages[index + 1]["content"].extend(missing_content_blocks)
204                         else:
205                             # The message following the toolUse was not a toolResult, so lets insert it
206                             messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
207                 # Fix orphaned toolResult missing toolUse (new logic)
208                 if any("toolResult" in content for content in message["content"]):
209                     tool_result_ids = [
210                         content["toolResult"]["toolUseId"] for content in message["content"] if "toolResult" in content
211                     ]
212 
213                     # Check if there are messages before the current toolResult message
214                     tool_use_ids_before = []
215                     if index - 1 >= 0:
216                         for c in messages[index - 1]["content"]:
217                             if "toolUse" in c:
218                                 tool_use_ids_before.append(c["toolUse"]["toolUseId"])
219 
220                     missing_tool_result_use_ids = list(set(tool_result_ids) - set(tool_use_ids_before))
221                     if missing_tool_result_use_ids:
222                         logger.warning(
223                             "Session message history has an orphaned toolResult with no preceding toolUse. "
224                             "Adding toolUse content blocks to create valid conversation."
225                         )
226                         missing_tool_use_blocks = generate_missing_tool_use_content(missing_tool_result_use_ids)
227                         # Insert the missing toolUse blocks before the current message
228                         messages.insert(index, {"role": "user", "content": missing_tool_use_blocks})
229         return messages
</patched>
```

---

# modification 3
Modify `S3SessionManager.list_messages` in `src/strands/session/s3_session_manager.py` to ensure that if the first retrieved message is a toolResult referring to a toolUse not included in the page, prepend the missing toolUse message or dummy message.

```
<file>src/strands/session/s3_session_manager.py</file>
<original>259     def list_messages(
260         self, session_id: str, agent_id: str, limit: Optional[int] = None, offset: int = 0, **kwargs: Any
261     ) -> List[SessionMessage]:
262         """List messages for an agent with pagination from S3."""
263         messages_prefix = f"{self._get_agent_path(session_id, agent_id)}messages/"
264         try:
265             paginator = self.client.get_paginator("list_objects_v2")
266             pages = paginator.paginate(Bucket=self.bucket, Prefix=messages_prefix)
267 
268             # Collect all message keys and extract their indices
269             message_index_keys: list[tuple[int, str]] = []
270             for page in pages:
271                 if "Contents" in page:
272                     for obj in page["Contents"]:
273                         key = obj["Key"]
274                         if key.endswith(".json") and MESSAGE_PREFIX in key:
275                             # Extract the filename part from the full S3 key
276                             filename = key.split("/")[-1]
277                             # Extract index from message_<index>.json format
278                             index = int(filename[len(MESSAGE_PREFIX) : -5])  # Remove prefix and .json suffix
279                             message_index_keys.append((index, key))
280 
281             # Sort by index and extract just the keys
282             message_keys = [k for _, k in sorted(message_index_keys)]
283 
284             # Apply pagination to keys before loading content
285             if limit is not None:
286                 message_keys = message_keys[offset : offset + limit]
287             else:
288                 message_keys = message_keys[offset:]
289 
290             # Load only the required message objects
291             messages: List[SessionMessage] = []
292             for key in message_keys:
293                 message_data = self._read_s3_object(key)
294                 if message_data:
295                     messages.append(SessionMessage.from_dict(message_data))
296 
297             return messages
298 
299         except ClientError as e:
300             raise SessionException(f"S3 error reading messages: {e}") from e
</original>
<patched>259     def list_messages(
260         self, session_id: str, agent_id: str, limit: Optional[int] = None, offset: int = 0, **kwargs: Any
261     ) -> List[SessionMessage]:
262         """List messages for an agent with pagination from S3."""
263         messages_prefix = f"{self._get_agent_path(session_id, agent_id)}messages/"
264         try:
265             paginator = self.client.get_paginator("list_objects_v2")
266             pages = paginator.paginate(Bucket=self.bucket, Prefix=messages_prefix)
267 
268             # Collect all message keys and extract their indices
269             message_index_keys: list[tuple[int, str]] = []
270             for page in pages:
271                 if "Contents" in page:
272                     for obj in page["Contents"]:
273                         key = obj["Key"]
274                         if key.endswith(".json") and MESSAGE_PREFIX in key:
275                             # Extract the filename part from the full S3 key
276                             filename = key.split("/")[-1]
277                             # Extract index from message_<index>.json format
278                             index = int(filename[len(MESSAGE_PREFIX) : -5])  # Remove prefix and .json suffix
279                             message_index_keys.append((index, key))
280 
281             # Sort by index and extract just the keys
282             message_keys = [k for _, k in sorted(message_index_keys)]
283 
284             # Apply pagination to keys before loading content
285             if limit is not None:
286                 message_keys = message_keys[offset : offset + limit]
287             else:
288                 message_keys = message_keys[offset:]
289 
290             # Load only the required message objects
291             messages: List[SessionMessage] = []
292             for key in message_keys:
293                 message_data = self._read_s3_object(key)
294                 if message_data:
295                     messages.append(SessionMessage.from_dict(message_data))
296 
297             # Fix toolResult orphaned from missing preceding toolUse message at the retrieval boundary
298             if messages and messages[0].content:
299                 first_message = messages[0]
300                 orphaned_tool_use_ids = []
301 
302                 # Collect toolUseIds from toolResults of the first_message
303                 for content_block in first_message.content:
304                     if isinstance(content_block, dict) and "toolResult" in content_block:
305                         tool_use_id = content_block["toolResult"].get("toolUseId")
306                         if tool_use_id:
307                             orphaned_tool_use_ids.append(tool_use_id)
308 
309                 if orphaned_tool_use_ids:
310                     # Look for toolUse messages among all message keys with index less than first message's id
311                     first_msg_id = first_message.message_id
312                     needed_tool_use_messages = []
313                     missing_tool_use_ids = []
314 
315                     # Create a map index->message to avoid multiple reads
316                     message_dict = {m.message_id: m for m in messages}
317 
318                     # For each toolUseId, try to find a message with that toolUse content earlier than first_msg_id
319                     for tool_use_id in orphaned_tool_use_ids:
320                         found = False
321                         # We look backward from first_msg_id - 1 downwards
322                         for check_id in range(first_msg_id - 1, -1, -1):
323                             if check_id in message_dict:
324                                 message_obj = message_dict[check_id]
325                             else:
326                                 # Load message from S3
327                                 message_key = self._get_message_path(session_id, agent_id, check_id)
328                                 message_data = self._read_s3_object(message_key)
329                                 if message_data:
330                                     message_obj = SessionMessage.from_dict(message_data)
331                                     message_dict[check_id] = message_obj
332                                 else:
333                                     continue
334                             # Check if this message has toolUse with matching toolUseId
335                             if any(
336                                 isinstance(content_block, dict)
337                                 and "toolUse" in content_block
338                                 and content_block["toolUse"].get("toolUseId") == tool_use_id
339                                 for content_block in message_obj.content
340                             ):
341                                 needed_tool_use_messages.append(message_obj)
342                                 found = True
343                                 break
344                         if not found:
345                             missing_tool_use_ids.append(tool_use_id)
346 
347                     # Sort toolUse messages by message_id ascending
348                     needed_tool_use_messages = sorted(needed_tool_use_messages, key=lambda m: m.message_id)
349 
350                     # Prepend found toolUse messages
351                     messages = needed_tool_use_messages + messages
352 
353                     # If there are missing toolUse messages (not found in S3), generate dummy contents and prepend a message
354                     if missing_tool_use_ids:
355                         from strands.tools._tool_helpers import generate_missing_tool_use_content
356                         dummy_tool_use_content = generate_missing_tool_use_content(missing_tool_use_ids)
357                         dummy_message_id = -1  # Use a negative or zero index to signal dummy/placeholder
358                         dummy_message = SessionMessage(
359                             role="user",
360                             content=dummy_tool_use_content,
361                             message_id=dummy_message_id,
362                         )
363                         messages = [dummy_message] + messages
364 
365             return messages
366 
367         except ClientError as e:
368             raise SessionException(f"S3 error reading messages: {e}") from e
</patched>
```

---

These changes address the problem by ensuring that toolUse and toolResult come paired in the messages returned from S3, avoiding the situation where toolResult events exist without the corresponding toolUse messages when pagination boundaries are hit. This prevents the validation error and preserves proper context during agent hydration.