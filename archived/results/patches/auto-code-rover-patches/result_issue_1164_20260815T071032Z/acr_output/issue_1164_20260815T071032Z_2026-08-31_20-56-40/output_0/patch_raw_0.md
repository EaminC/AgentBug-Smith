The main issue is that the method `list_messages()` currently fetches message objects sequentially, which is slow for many messages due to the network latency per request. The improvement is to fetch messages in parallel using `concurrent.futures.ThreadPoolExecutor`. 

Key points for the fix:
- Import `concurrent.futures.ThreadPoolExecutor`.
- After sorting and applying pagination to the message keys, submit parallel fetch tasks.
- Collect results and maintain the order by pairing each future with its index and key.
- Handle individual fetch failures gracefully; if a fetch returns None or raises, skip that message but don't stop the whole operation.
- Convert successful fetched data to `SessionMessage` instances.
- Return the messages in the order of message index.
- Keep existing exception handling for the overall operation.

We only need to modify the `list_messages` method and add the necessary import at the top of the file.

---

# modification 1: Add import
```
<file>src/strands/session/s3_session_manager.py</file>
<original>import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
import json
from typing import Any, cast

SESSION_PREFIX = "session_"
AGENT_PREFIX = "agent_"
MESSAGE_PREFIX = "message_"
MULTI_AGENT_PREFIX = "multi_agent_"</original>
<patched>import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
import json
from typing import Any, cast
import concurrent.futures

SESSION_PREFIX = "session_"
AGENT_PREFIX = "agent_"
MESSAGE_PREFIX = "message_"
MULTI_AGENT_PREFIX = "multi_agent_"</patched>
```

# modification 2: Parallelize list_messages
```
<file>src/strands/session/s3_session_manager.py</file>
<original>259     def list_messages(
260         self, session_id: str, agent_id: str, limit: int | None = None, offset: int = 0, **kwargs: Any
261     ) -> list[SessionMessage]:
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
291             messages: list[SessionMessage] = []
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
260         self, session_id: str, agent_id: str, limit: int | None = None, offset: int = 0, **kwargs: Any
261     ) -> list[SessionMessage]:
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
281             # Sort by index and extract just the keys and indices for pagination
282             sorted_message_index_keys = sorted(message_index_keys)
283 
284             # Apply pagination to keys before loading content
285             if limit is not None:
286                 paginated_message_index_keys = sorted_message_index_keys[offset : offset + limit]
287             else:
288                 paginated_message_index_keys = sorted_message_index_keys[offset:]
289 
290             # Load message objects in parallel using ThreadPoolExecutor
291             messages: list[SessionMessage] = []
292             with concurrent.futures.ThreadPoolExecutor() as executor:
293                 # Submit fetch callables and keep track of index for ordering
294                 future_to_index_key = {
295                     executor.submit(self._read_s3_object, key): (index, key)
296                     for index, key in paginated_message_index_keys
297                 }
298                 # Collect results as they complete, preserving order by index afterwards
299                 fetched_results = []
300                 for future in concurrent.futures.as_completed(future_to_index_key):
301                     index, key = future_to_index_key[future]
302                     try:
303                         message_data = future.result()
304                         if message_data:
305                             fetched_results.append((index, SessionMessage.from_dict(message_data)))
306                     except Exception:
307                         # Ignore individual message loading errors; continue
308                         pass
309 
310             # Sort by message index to preserve order
311             messages = [msg for _, msg in sorted(fetched_results, key=lambda x: x[0])]
312 
313             return messages
314 
315         except ClientError as e:
316             raise SessionException(f"S3 error reading messages: {e}") from e
</patched>
```