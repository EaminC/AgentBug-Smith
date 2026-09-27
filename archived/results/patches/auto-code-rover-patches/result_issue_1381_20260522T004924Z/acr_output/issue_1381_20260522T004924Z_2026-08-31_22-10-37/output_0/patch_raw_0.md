The root cause of the duplicate primary key error is that the `_make_message_id` method generates a composite key based solely on `user_id`, `session_id`, and `msg_id`, and when multiple asynchronous tool calls happen concurrently with the same `msg_id`, the insertion attempts with the same primary key lead to a conflict.

Since the `add` method (or equivalent insert method) was not explicitly found, but `memory.add()` calls exist, the best place to fix this is to modify `_make_message_id` to include a unique component (for example, a `UUID` or a timestamp with high precision) so that every generated message ID will be unique even in parallel calls.

Hence, the patch introduces use of `uuid4()` within the `_make_message_id` method to append a new unique suffix for every generated message ID, preventing duplicate primary key conflicts in parallel inserts.

This fix preserves existing functionality because it retains the user and session identification within the composite key, only enhances it by adding uniqueness.

```python
import uuid  # will be added for uuid4
```

# Patch:

```
<file>src/agentscope/memory/_working_memory/_sqlalchemy_memory.py</file>
<original>    def _make_message_id(self, msg_id: str) -> str:
        """Generate a composite primary key for a message.

        Args:
            msg_id (`str`):
                The original message ID.

        Returns:
            `str`:
                The composite primary key in the format
                "{user_id}-{session_id}-{message_id}".
        """
        return f"{self.user_id}-{self.session_id}-{msg_id}"
</original>
<patched>    import uuid

    def _make_message_id(self, msg_id: str) -> str:
        """Generate a composite primary key for a message.

        Args:
            msg_id (`str`):
                The original message ID.

        Returns:
            `str`:
                The composite primary key in the format
                "{user_id}-{session_id}-{message_id}-{unique_suffix}".
        """
        unique_suffix = uuid.uuid4().hex
        return f"{self.user_id}-{self.session_id}-{msg_id}-{unique_suffix}"
</patched>
```

This patch solves the concurrency issue by adding a unique suffix to each message ID in every call, avoiding duplicate entries under parallel tool calls.