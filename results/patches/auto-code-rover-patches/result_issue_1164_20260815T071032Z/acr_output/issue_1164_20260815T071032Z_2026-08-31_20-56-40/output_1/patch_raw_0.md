The main improvement is to parallelize the retrieval of messages in the `list_messages()` method. The current implementation retrieves each message sequentially, which is slow for large number of messages. We will use `ThreadPoolExecutor` from `concurrent.futures` to fetch the messages concurrently, while maintaining the order of messages (by their index). We also must handle individual failures gracefully by skipping failed reads and continuing. We will apply pagination before the reads (as is done currently). The rest of the method's logic and error handling remains unchanged.

We will import `concurrent.futures` at the top of the file and then modify only the `list_messages()` method accordingly.

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
<patched>import concurrent.futures

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
            message_keys = [k for _, k in sorted(message_index_keys)]

            # Apply pagination to keys before loading content
            if limit is not None:
                message_keys = message_keys[offset : offset + limit]
            else:
                message_keys = message_keys[offset:]

            # Load required message objects using ThreadPoolExecutor to parallelize fetches
            messages: list[SessionMessage] = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit all fetch tasks
                future_to_key = {
                    executor.submit(self._read_s3_object, key): key for key in message_keys
                }

                # Collect results in order by index to preserve order
                # Because futures may complete out of order,
                # we create a dict indexed by key to retrieve results ordered later.
                results_dict: dict[str, SessionMessage] = {}

                for future in concurrent.futures.as_completed(future_to_key):
                    key = future_to_key[future]
                    try:
                        message_data = future.result()
                    except Exception:
                        # Skip failed reads silently or extend logging as needed
                        continue
                    if message_data:
                        try:
                            results_dict[key] = SessionMessage.from_dict(message_data)
                        except Exception:
                            # Skip invalid message data
                            continue

                # Append messages in original order of keys
                for key in message_keys:
                    msg = results_dict.get(key)
                    if msg:
                        messages.append(msg)

            return messages

        except ClientError as e:
            raise SessionException(f"S3 error reading messages: {e}") from e
</patched>
```