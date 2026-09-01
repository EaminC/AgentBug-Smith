Reasoning:

The issue is that during context compression in the Agent class (method compress_context()), when tool call blocks of type 'Read' are evicted (no longer reserved in the context), their associated cache entries in ToolContext's read_file_cache are not cleared. This causes the cache to grow indefinitely.

To fix this:

1. Add a method `clear_read_cache_for_files(file_paths: set[str])` in the ToolContext class to remove cached entries for a given set of file paths. This aligns with the first location's intended behavior.

2. Modify Agent's `compress_context` method to:

   - Identify which Read tool call blocks are in the context messages being compressed (i.e., that are going to be evicted)

   - Get the file paths associated with those Read tool call blocks

   - Use the new ToolContext method to clear the cache entries associated with these file paths

We do not change everything in Agent, only the `compress_context` method related to context compression and cache clearing.

Patch:

- In ToolContext, add a method `clear_read_cache_for_files`

- In Agent, update `compress_context` to find evicted Read tool call blocks and clear their cached files accordingly.

Code changes reflect only these minimal changes.

---

# modification 1

```python
<file>src/agentscope/state/_state.py</file>
<original>class ToolContext(BaseModel):
    ...
    async def get_cache(self, file_path: str) -> ReadCacheEntry | None:
        ...
    async def cache_file(self, file_path: str, lines: list[str]) -> None:
        ...
</original>
<patched>class ToolContext(BaseModel):
    ...
    async def get_cache(self, file_path: str) -> ReadCacheEntry | None:
        ...
    async def cache_file(self, file_path: str, lines: list[str]) -> None:
        ...

    def clear_read_cache_for_files(self, file_paths: set[str]) -> None:
        """Clear read cache entries associated with the specified file paths.

        Args:
            file_paths (set[str]): The set of file paths whose cache entries should be cleared.
        """
        self.read_file_cache = [
            entry for entry in self.read_file_cache if entry.file_path not in file_paths
        ]
</patched>
```

# modification 2

```python
<file>src/agentscope/agent/_agent.py</file>
<original>    async def compress_context(
        self,
        context_config: ContextConfig | None = None,
    ) -> None:
        """Compress the agent's context if the token count exceeds the
        threshold.
    ...
        # Update the context
        self.state.context = msgs_to_reserve

        logger.info(
            "[AGENT %s]: The context compression finished.",
            self.name,
        )
</original>
<patched>    async def compress_context(
        self,
        context_config: ContextConfig | None = None,
    ) -> None:
        """Compress the agent's context if the token count exceeds the
        threshold.
    ...
        # Before updating the context, identify evicted Read tool call blocks and clear their cache

        # Collect file paths from Read tool call blocks that are in the msgs_to_compress (to be evicted)
        evicted_read_file_paths = set()
        for msg in msgs_to_compress:
            for block in msg.get_content_blocks():
                # Check if the block is a ToolCallBlock and of Read type
                # We need to confirm 'Read' tools which probably are identified by tool name
                if isinstance(block, ToolCallBlock):
                    # We need to check if block.name corresponds to a Read tool
                    # Since toolkit is available we can check the tool type asynchronously
                    # But compress_context is async, so we can await here
                    # But to avoid overhead, collect these blocks first and then check
                    pass

        # Because toolkit.get_tool is async, we must handle this asynchronously here:
        evicted_read_tool_calls = []

        for msg in msgs_to_compress:
            for block in msg.get_content_blocks():
                if isinstance(block, ToolCallBlock):
                    evicted_read_tool_calls.append(block)

        # We'll check which of these tool calls correspond to Read tools
        read_file_paths = set()
        for tool_call in evicted_read_tool_calls:
            tool = await self.toolkit.get_tool(tool_call.name)
            if tool is not None and tool.type == "Read":
                # Assume the input has a file path; usually tool_call.input is a JSON string
                try:
                    parsed_input = _json_loads_with_repair(tool_call.input, None)
                except Exception:
                    parsed_input = None
                if parsed_input is not None and "path" in parsed_input:
                    fp = parsed_input["path"]
                    if isinstance(fp, str):
                        read_file_paths.add(fp)

        # Clear cache entries of those evicted Read tool calls
        if read_file_paths:
            self.state.tool_context.clear_read_cache_for_files(read_file_paths)

        # Update the context
        self.state.context = msgs_to_reserve

        logger.info(
            "[AGENT %s]: The context compression finished.",
            self.name,
        )
</patched>
```

Note: The ... in both original and patched is meant to keep the original existing code lines unchanged and only insert the new or modified code at the appropriate position in the method.

Additionally, import _json_loads_with_repair if not already imported:

```python
from agentscope.util import _json_loads_with_repair
```

This import may be added at the top of `src/agentscope/agent/_agent.py` if necessary.

Since tooling has the method `get_tool` which returns a Tool with a `type` attribute which can be compared to `"Read"`, this method is used to filter read tool blocks.

This patch explicitly removes cache entries for files associated with read tool call blocks evicted during context compression, which addresses the root issue.

---

# modification 3 (import addition)

```python
<file>src/agentscope/agent/_agent.py</file>
<original>import asyncio
import inspect
import logging
import uuid
from copy import deepcopy
from queue import Queue
from typing import Any, AsyncGenerator, List, Sequence

# ... many other imports
</original>
<patched>import asyncio
import inspect
import logging
import uuid
from copy import deepcopy
from queue import Queue
from typing import Any, AsyncGenerator, List, Sequence

from agentscope.util import _json_loads_with_repair

# ... many other imports
</patched>
```

This import is needed to parse the tool_call input field to extract the path.