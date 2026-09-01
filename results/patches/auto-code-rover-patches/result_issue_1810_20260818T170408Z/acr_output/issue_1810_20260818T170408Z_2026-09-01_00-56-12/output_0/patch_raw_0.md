The issue arises because the current code only tracks tool use blocks from the "contentBlockStart" event, specifically looking for a toolUse start event there. However, in certain edge cases, "contentBlockDelta" events can also contain toolUse data, and these are not currently monitored. This causes the `has_tool_use` flag to remain False in those cases, and the code incorrectly does not override the stop reason "end_turn" to "tool_use" when the messageStop event arrives.

The fix is to extend the detection logic to also set `has_tool_use = True` when a "contentBlockDelta" chunk contains a toolUse key. This redundant tracking will capture tool use appearances, regardless of whether they appear in contentBlockStart or contentBlockDelta events, so that the stop reason override logic will fire correctly.

This patch modifies only the relevant part inside the `_stream` method of `BedrockModel` where the streaming response chunks are processed.

---

```
<file>src/strands/models/bedrock.py</file>
<original>                # Track if we see tool use events
                if "contentBlockStart" in chunk and chunk["contentBlockStart"].get("start", {}).get("toolUse"):
                    has_tool_use = True
</original>
<patched>                # Track if we see tool use events
                if "contentBlockStart" in chunk and chunk["contentBlockStart"].get("start", {}).get("toolUse"):
                    has_tool_use = True
                if "contentBlockDelta" in chunk and chunk["contentBlockDelta"].get("delta", {}).get("toolUse"):
                    has_tool_use = True
</patched>
</file>
```
