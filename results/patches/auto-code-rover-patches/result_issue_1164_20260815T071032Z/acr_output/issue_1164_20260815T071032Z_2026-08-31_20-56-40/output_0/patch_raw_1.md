# Reasoning:
To improve the performance of `list_messages`, we will import `ThreadPoolExecutor` from `concurrent.futures` and modify `list_messages` to fetch messages concurrently using a thread pool. Since the order of messages matters, we'll associate each future with its corresponding message index. After all messages are fetched, we will sort by the original indices and build the list of `SessionMessage` instances. We will also include error handling inside the thread worker retrieval so that failures in fetching some messages do not abort the entire process and just skip those messages. The pagination logic remains the same: we paginate S3 keys first before fetching.

The `_read_s3_object` function is already thread-safe and handles exceptions appropriately, so we do not need to modify it.

# modification 1: Add import statement for `ThreadPoolExecutor` at the top of s3_session_manager.py

```
<file>src/strands/session/s3_session_manager.py</file>
<original>import json
from typing import Any, cast
from botocore.exceptions import ClientError
import boto3
from botocore.config import Config as BotocoreConfig
from strands.session.exceptions import SessionException
from strands.session.model import Session, SessionAgent, SessionMessage
from strands.session.repository import RepositorySessionManager, SessionRepository
from strands.session._constants import AGENT_PREFIX, MESSAGE_PREFIX, MULTI_AGENT_PREFIX, SESSION_PREFIX
from strands.session._utils import _identifier
</original>
<patched>import json
from typing import Any, cast
from botocore.exceptions import ClientError
import boto3
from botocore.config import Config as BotocoreConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
from strands.session.exceptions import SessionException
from strands.session.model import Session, SessionAgent, SessionMessage
from strands.session.repository import RepositorySessionManager, SessionRepository
from strands.session._constants import AGENT_PREFIX, MESSAGE_PREFIX, MULTI_AGENT_PREFIX, SESSION_PREFIX
from strands.session._utils import _identifier
</patched>
```

# modification 2: Update `list_messages` to parallelize message fetches with ThreadPoolExecutor, keep order, and handle errors gracefully

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
281             # Sort by index and extract just the keys
282             sorted_index_keys = sorted(message_index_keys)
283 
284             # Apply pagination to keys before loading content
285             if limit is not None:
286                 sorted_index_keys = sorted_index_keys[offset : offset + limit]
287             else:
288                 sorted_index_keys = sorted_index_keys[offset:]
289 
290             messages: list[SessionMessage] = []
291             with ThreadPoolExecutor() as executor:
292                 # Map futures to their indices to preserve order
293                 future_to_index = {
294                     executor.submit(self._read_s3_object, key): index for index, key in sorted_index_keys
295                 }
296 
297                 # Collect results as they complete but store in dict keyed by index
298                 results = {}
299                 for future in as_completed(future_to_index):
300                     index = future_to_index[future]
301                     try:
302                         message_data = future.result()
303                         if message_data:
304                             results[index] = SessionMessage.from_dict(message_data)
305                     except SessionException:
306                         # Skip failed reads silently
307                         pass
308 
309             # Collect messages in order of indices
310             messages = [results[index] for index, _ in sorted_index_keys if index in results]
311 
312             return messages
313 
314         except ClientError as e:
315             raise SessionException(f"S3 error reading messages: {e}") from e
</patched>
```