The issue is that when fixing orphaned toolUse blocks, the code inserts or extends toolResult blocks incorrectly, resulting in an excess number of toolResult blocks compared to toolUse blocks from the previous assistant message. This fails Bedrock’s validation.

Looking at the current fix logic, it fetches all toolUse IDs in the assistant message at index i and compares them with existing toolResult IDs in the next user message at index i+1. For missing toolUse IDs, it calls generate_missing_tool_result_content() and appends or inserts the corresponding toolResult blocks.

However, the bug often arises because the next message can already partially contain toolResult blocks that do not correspond one-to-one to the toolUse blocks of the previous message or due to duplication.

To fix this:

- We should count how many toolUse blocks exist in the current message.

- We should count how many toolResult blocks exist in the next message that correspond to these toolUse blocks.

- The key requirement: the number of toolResult blocks must NOT exceed the number of toolUse blocks in the preceding assistant message.

Currently, the code deduces missing_tool_use_ids from set differences of IDs. But because IDs can repeat or mismatch, a set difference isn’t always sufficient to conclude how many blocks to add.

A more straightforward fix is to:

- Count number of toolUse blocks in the current message (tool_use_count)

- Count number of toolResult blocks in the next message that have matching toolUseIds (tool_result_count_matching)

- The number of missing toolResults to add = tool_use_count - tool_result_count_matching

This ensures matching counts, and if the next message already contains more toolResults than toolUse blocks, do nothing (possibly log a warning/error?).

So the fix is:

- For each toolUseId in the current message, count how many times it appears (some may be duplicate IDs).

- For the next message, count how many toolResult with matching toolUseId exist.

- Add only missing counts to next message, never exceeding the number of toolUse blocks.

Since toolUseId may not be unique across multiple blocks, it may be easier to compute counts by enumerating.

Alternatively, given the current approach stores toolUseId distinctly per block, defining equality via IDs should be fine, just ensure missing blocks counting is exact.

We can modify the loop at _fix_broken_tool_use to build a list of missing toolUseIds matching the counts, instead of set difference.

Implementation details:

- Build a list of all toolUseIds in current message, including duplicates.

- Build a list of all toolResult toolUseIds in next message.

- For each toolUseId in toolUseIds, if it appears in toolResultIds, remove one occurrence from toolResultIds list.

- The remaining toolUseIds are missing.

This way, we respect duplicate counts of the same ID.

Then generate toolResult content blocks only for these missing IDs.

If the next message's content is not a toolResult message, insert a new one.

Otherwise, append missing blocks.

This will fix the problem of excess toolResult blocks and ensure exact matching counts.

---

Patch only _fix_broken_tool_use method in repository_session_manager.py.

---

Patch:

```
<file>strands-py/src/strands/session/repository_session_manager.py</file>
<original>    def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
        """Fix broken tool use/result pairs in message history.

        This method handles two issues:
        1. Orphaned toolUse messages without corresponding toolResult.
           Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
           This method retroactively fixes that issue by adding a tool_result outside of session management.
           After 1.15.0, this bug is no longer present.
        2. Orphaned toolResult messages without corresponding toolUse (e.g., when pagination truncates messages)

        Args:
            messages: The list of messages to fix
            agent_id: The agent ID for fetching previous messages
            removed_message_count: Number of messages removed by the conversation manager

        Returns:
            Fixed list of messages with proper tool use/result pairs
        """
        # First, check if the oldest message has orphaned toolResult (no preceding toolUse) and remove it.
        if messages:
            first_message = messages[0]
            if first_message["role"] == "user" and any("toolResult" in content for content in first_message["content"]):
                logger.warning(
                    "Session message history starts with orphaned toolResult with no preceding toolUse. "
                    "This typically happens when messages are truncated due to pagination limits. "
                    "Removing orphaned toolResult message to maintain valid conversation structure."
                )
                messages.pop(0)

        # Then check for orphaned toolUse messages. Snapshot the eligible indices before
        # iterating so that inserting a toolResult (which shifts later indices) does not
        # cause the loop to skip a subsequent orphaned toolUse. The trailing message is
        # excluded from the snapshot because that case is handled in the agent class when
        # a new prompt arrives, so we do not synthesize a toolResult into persisted
        # history for it here. Walking in reverse means each insert only shifts already-
        # processed positions, so the original snapshot indices remain valid.
        original_last_index = len(messages) - 1
        tool_use_indices = [
            index
            for index, message in enumerate(messages)
            if index < original_last_index and any("toolUse" in content for content in message["content"])
        ]
        for index in reversed(tool_use_indices):
            message = messages[index]
            tool_use_ids = [
                content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
            ]

            # Check the toolResult ids already present in the next message.
            tool_result_ids = [
                content["toolResult"]["toolUseId"]
                for content in messages[index + 1]["content"]
                if "toolResult" in content
            ]

            missing_tool_use_ids = list(set(tool_use_ids) - set(tool_result_ids))
            if not missing_tool_use_ids:
                continue

            logger.warning(
                "Session message history has an orphaned toolUse with no toolResult. "
                "Adding toolResult content blocks to create valid conversation."
            )
            missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)

            if tool_result_ids:
                # If there were any toolResult ids, that means only some of the content blocks are missing
                messages[index + 1]["content"].extend(missing_content_blocks)
            else:
                # The message following the toolUse was not a toolResult, so lets insert it
                messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
        return messages
</original>
<patched>    def _fix_broken_tool_use(self, messages: list[Message]) -> list[Message]:
        """Fix broken tool use/result pairs in message history.

        This method handles two issues:
        1. Orphaned toolUse messages without corresponding toolResult.
           Before 1.15.0, strands had a bug where they persisted sessions with a potentially broken messages array.
           This method retroactively fixes that issue by adding a tool_result outside of session management.
           After 1.15.0, this bug is no longer present.
        2. Orphaned toolResult messages without corresponding toolUse (e.g., when pagination truncates messages)

        Args:
            messages: The list of messages to fix
            agent_id: The agent ID for fetching previous messages
            removed_message_count: Number of messages removed by the conversation manager

        Returns:
            Fixed list of messages with proper tool use/result pairs
        """
        # First, check if the oldest message has orphaned toolResult (no preceding toolUse) and remove it.
        if messages:
            first_message = messages[0]
            if first_message["role"] == "user" and any("toolResult" in content for content in first_message["content"]):
                logger.warning(
                    "Session message history starts with orphaned toolResult with no preceding toolUse. "
                    "This typically happens when messages are truncated due to pagination limits. "
                    "Removing orphaned toolResult message to maintain valid conversation structure."
                )
                messages.pop(0)

        # Then check for orphaned toolUse messages. Snapshot the eligible indices before
        # iterating so that inserting a toolResult (which shifts later indices) does not
        # cause the loop to skip a subsequent orphaned toolUse. The trailing message is
        # excluded from the snapshot because that case is handled in the agent class when
        # a new prompt arrives, so we do not synthesize a toolResult into persisted
        # history for it here. Walking in reverse means each insert only shifts already-
        # processed positions, so the original snapshot indices remain valid.
        original_last_index = len(messages) - 1
        tool_use_indices = [
            index
            for index, message in enumerate(messages)
            if index < original_last_index and any("toolUse" in content for content in message["content"])
        ]
        for index in reversed(tool_use_indices):
            message = messages[index]
            # Get list of all toolUseIds (including duplicates)
            tool_use_ids = [
                content["toolUse"]["toolUseId"] for content in message["content"] if "toolUse" in content
            ]
            # Next message
            next_message = messages[index + 1]
            # Get list of all toolResult toolUseIds (including duplicates) in next message
            tool_result_ids = [
                content["toolResult"]["toolUseId"]
                for content in next_message["content"]
                if "toolResult" in content
            ]

            # Count missing toolUseIds factoring duplicates properly
            remaining_tool_result_ids = tool_result_ids.copy()
            missing_tool_use_ids = []
            for tuid in tool_use_ids:
                if tuid in remaining_tool_result_ids:
                    remaining_tool_result_ids.remove(tuid)
                else:
                    missing_tool_use_ids.append(tuid)

            if not missing_tool_use_ids:
                continue

            logger.warning(
                "Session message history has an orphaned toolUse with no toolResult. "
                "Adding toolResult content blocks to create valid conversation."
            )
            missing_content_blocks = generate_missing_tool_result_content(missing_tool_use_ids)

            # Determine if next message is already a toolResult message (all content blocks "toolResult")
            if all("toolResult" in content for content in next_message["content"]):
                # Extend existing toolResult content blocks with missing ones
                next_message["content"].extend(missing_content_blocks)
            else:
                # Insert new toolResult message after current index
                messages.insert(index + 1, {"role": "user", "content": missing_content_blocks})
        return messages
</patched>
```