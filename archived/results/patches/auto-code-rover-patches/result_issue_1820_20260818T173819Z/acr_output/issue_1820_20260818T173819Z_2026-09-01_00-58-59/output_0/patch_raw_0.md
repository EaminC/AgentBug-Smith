The issue arises because cache points are always appended at the end of the last assistant message content, which leads to an invalid placement if the last content block is a reasoningContent block. Bedrock API expects cache points to be placed before any reasoning content blocks, not after.

The fix requires modifying the `_inject_cache_point` method to:
- Remove any existing cache points in all messages first (existing behavior).
- Then, when adding a new cache point, if the last assistant message's content ends with a reasoningContent block, insert the cache point immediately before that last reasoningContent block instead of appending at the end.
- Otherwise, append as before.

This minimal change directly addresses the problem without affecting other logic.

---

```
<file>src/strands/models/bedrock.py</file>
<original>    def _inject_cache_point(self, messages: list[dict[str, Any]]) -> None:
        """Inject a cache point at the end of the last assistant message.

        Args:
            messages: List of messages to inject cache point into (modified in place).
        """
        if not messages:
            return

        last_assistant_idx: int | None = None
        for msg_idx, msg in enumerate(messages):
            content = msg.get("content", [])
            for block_idx, block in reversed(list(enumerate(content))):
                if "cachePoint" in block:
                    del content[block_idx]
                    logger.warning(
                        "msg_idx=<%s>, block_idx=<%s> | stripped existing cache point (auto mode manages cache points)",
                        msg_idx,
                        block_idx,
                    )
            if msg.get("role") == "assistant":
                last_assistant_idx = msg_idx

        if last_assistant_idx is not None and messages[last_assistant_idx].get("content"):
            messages[last_assistant_idx]["content"].append({"cachePoint": {"type": "default"}})
            logger.debug("msg_idx=<%s> | added cache point to last assistant message", last_assistant_idx)
</original>
<patched>    def _inject_cache_point(self, messages: list[dict[str, Any]]) -> None:
        """Inject a cache point at the end of the last assistant message.

        Args:
            messages: List of messages to inject cache point into (modified in place).
        """
        if not messages:
            return

        last_assistant_idx: int | None = None
        for msg_idx, msg in enumerate(messages):
            content = msg.get("content", [])
            for block_idx, block in reversed(list(enumerate(content))):
                if "cachePoint" in block:
                    del content[block_idx]
                    logger.warning(
                        "msg_idx=<%s>, block_idx=<%s> | stripped existing cache point (auto mode manages cache points)",
                        msg_idx,
                        block_idx,
                    )
            if msg.get("role") == "assistant":
                last_assistant_idx = msg_idx

        # Insert cache point before the last reasoningContent block if present, else append normally
        if last_assistant_idx is not None and messages[last_assistant_idx].get("content"):
            content = messages[last_assistant_idx]["content"]
            if content and "reasoningContent" in content[-1]:
                content.insert(len(content) - 1, {"cachePoint": {"type": "default"}})
                logger.debug("msg_idx=<%s> | inserted cache point before reasoning content in last assistant message", last_assistant_idx)
            else:
                content.append({"cachePoint": {"type": "default"}})
                logger.debug("msg_idx=<%s> | added cache point to last assistant message", last_assistant_idx)
</patched>
```