I will enhance the `list_messages` method in `S3SessionManager` to fetch message files from S3 concurrently using `ThreadPoolExecutor` from the `concurrent.futures` module for better performance when there are many messages.

Reasoning:
- The original implementation fetches messages sequentially, resulting in high latency for large numbers of messages.
- Using `ThreadPoolExecutor` to issue concurrent gets will significantly reduce wait time due to network I/O.
- We will map futures to keys and collect results as they complete.
- We preserve the ordering by associating each fetch with its original index before sorting.
- Errors for individual messages will be caught and ignored so that one failure won't stop the entire process.
- The pagination and sorting logic remain unchanged.
- We'll import `ThreadPoolExecutor` and `as_completed` as needed.

---

# modification 1
```
<file>src/strands/session/s3_session_manager.py</file>
<original>    def list_messages(
        self, session_id: str, agent_id: str, limit: int | None = None, offset: int = 0, **kwargs: Any
    ) -> list[SessionMessage]:
        """List messages for an agent with pagination from S3."""
        messages_prefix = f"{self._get_agent_path(session_id, agent_id)}messages/"
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=messages_prefix)

            # Collect all message keys and extract their indices
            message_index_keys: list[tuple[int, str]] = []
            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if key.endswith(".json") and MESSAGE_PREFIX in key:
                            # Extract the filename part from the full S3 key
                            filename = key.split("/")[-1]
                            # Extract index from message_<index>.json format
                            index = int(filename[len(MESSAGE_PREFIX) : -5])  # Remove prefix and .json suffix
                            message_index_keys.append((index, key))

            # Sort by index and extract just the keys
            message_keys = [k for _, k in sorted(message_index_keys)]

            # Apply pagination to keys before loading content
            if limit is not None:
                message_keys = message_keys[offset : offset + limit]
            else:
                message_keys = message_keys[offset:]

            # Load only the required message objects
            messages: list[SessionMessage] = []
            for key in message_keys:
                message_data = self._read_s3_object(key)
                if message_data:
                    messages.append(SessionMessage.from_dict(message_data))

            return messages

        except ClientError as e:
            raise SessionException(f"S3 error reading messages: {e}") from e
</original>
<patched>    from concurrent.futures import ThreadPoolExecutor, as_completed

    def list_messages(
        self, session_id: str, agent_id: str, limit: int | None = None, offset: int = 0, **kwargs: Any
    ) -> list[SessionMessage]:
        """List messages for an agent with pagination from S3."""
        messages_prefix = f"{self._get_agent_path(session_id, agent_id)}messages/"
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix=messages_prefix)

            # Collect all message keys and extract their indices
            message_index_keys: list[tuple[int, str]] = []
            for page in pages:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        key = obj["Key"]
                        if key.endswith(".json") and MESSAGE_PREFIX in key:
                            # Extract the filename part from the full S3 key
                            filename = key.split("/")[-1]
                            # Extract index from message_<index>.json format
                            index = int(filename[len(MESSAGE_PREFIX) : -5])  # Remove prefix and .json suffix
                            message_index_keys.append((index, key))

            # Sort by index and extract just the keys
            sorted_message_index_keys = sorted(message_index_keys)

            # Apply pagination to keys before loading content and keep indices
            if limit is not None:
                paginated = sorted_message_index_keys[offset : offset + limit]
            else:
                paginated = sorted_message_index_keys[offset:]

            # Separate the indices and keys
            indices_with_keys = paginated

            messages: list[SessionMessage] = []

            # Use ThreadPoolExecutor to load the messages concurrently
            with ThreadPoolExecutor() as executor:
                # Map futures to their indices to preserve ordering
                future_to_index = {
                    executor.submit(self._read_s3_object, key): idx for idx, key in indices_with_keys
                }

                results = []
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        message_data = future.result()
                    except Exception:
                        # Log the error or ignore the failure for this particular message
                        message_data = None
                    results.append((idx, message_data))

            # Sort results by index to maintain message order
            results.sort(key=lambda pair: pair[0])

            for _, message_data in results:
                if message_data:
                    messages.append(SessionMessage.from_dict(message_data))

            return messages

        except ClientError as e:
            raise SessionException(f"S3 error reading messages: {e}") from e
</patched>
```