```
<file>src/agentscope/state/_state.py</file>
<original>65     async def cache_file(self, file_path: str, lines: list[str]) -> None:
66         """Cache file content with LRU eviction.
67 
68         Args:
69             file_path: The absolute path of the file.
70             lines: The lines of the file content.
71         """
72         try:
73             updated_at = await aiofiles.os.path.getmtime(file_path)
74         except Exception:
75             # Cannot get mtime, skip caching
76             return
77 
78         # Calculate size in KB
79         new_entry_bytes = (
80             sum(len(line.encode("utf-8")) for line in lines) / 1024
81         )
82 
83         # Remove existing cache for this file if present
84         self.read_file_cache = [
85             entry
86             for entry in self.read_file_cache
87             if entry.file_path != file_path
88         ]
89 
90         # Evict the oldest entries if exceeding max_cache_files
91         while len(self.read_file_cache) >= self.max_cache_files:
92             self.read_file_cache.pop(0)
93 
94         # Evict the oldest entries if exceeding max_cache_bytes
95         current_size = sum(entry.bytes for entry in self.read_file_cache)
96         while (
97             self.read_file_cache
98             and current_size + new_entry_bytes > self.max_cache_bytes
99         ):
100             removed = self.read_file_cache.pop(0)
101             current_size -= removed.bytes
102 
103         # Add new entry to the end (most recent)
104         self.read_file_cache.append(
105             ReadCacheEntry(
106                 lines=lines,
107                 updated_at=updated_at,
108                 bytes=new_entry_bytes,
109                 file_path=file_path,
110             ),
111         )
</original>
<patched>65     async def cache_file(self, file_path: str, lines: list[str]) -> None:
66         """Cache file content with LRU eviction.
67 
68         Args:
69             file_path: The absolute path of the file.
70             lines: The lines of the file content.
71         """
72         try:
73             updated_at = await aiofiles.os.path.getmtime(file_path)
74         except Exception:
75             # Cannot get mtime, skip caching
76             return
77 
78         # Calculate size in KB
79         new_entry_bytes = (
80             sum(len(line.encode("utf-8")) for line in lines) / 1024
81         )
82 
83         # Remove existing cache for this file if present
84         self.read_file_cache = [
85             entry
86             for entry in self.read_file_cache
87             if entry.file_path != file_path
88         ]
89 
90         # Evict the oldest entries if exceeding max_cache_files
91         while len(self.read_file_cache) >= self.max_cache_files:
92             self.read_file_cache.pop(0)
93 
94         # Evict the oldest entries if exceeding max_cache_bytes
95         current_size = sum(entry.bytes for entry in self.read_file_cache)
96         while (
97             self.read_file_cache
98             and current_size + new_entry_bytes > self.max_cache_bytes
99         ):
100             removed = self.read_file_cache.pop(0)
101             current_size -= removed.bytes
102 
103         # Add new entry to the end (most recent)
104         self.read_file_cache.append(
105             ReadCacheEntry(
106                 lines=lines,
107                 updated_at=updated_at,
108                 bytes=new_entry_bytes,
109                 file_path=file_path,
110             ),
111         )
112
113     def clear_cache_by_file_path(self, file_path: str) -> None:
114         """Clear the cached file content by file path."""
115         self.read_file_cache = [
116             entry for entry in self.read_file_cache if entry.file_path != file_path
117         ]
</patched>
</file>

<file>src/agentscope/agent/_agent.py</file>
<original>439         # Update the context
440         self.state.context = msgs_to_reserve
441 
442         logger.info(
443             "[AGENT %s]: The context compression finished.",
444             self.name,
445         )</original>
<patched>439         # Update the context
440         # Identify evicted Read tool call blocks and clear associated read cache
441         evicted_blocks = set(msg.id for msg in self.state.context if isinstance(msg, ToolCallBlock)) - set(msg.id for msg in msgs_to_reserve if isinstance(msg, ToolCallBlock))
442         for block in self.state.context:
443             if block.id in evicted_blocks and isinstance(block, ToolCallBlock):
444                 if block.name == "read":
445                     # Clear cached file content associated with this tool call block's input file path
446                     file_path = block.input
447                     self.state.clear_cache_by_file_path(file_path)
448 
449         self.state.context = msgs_to_reserve
450 
451         logger.info(
452             "[AGENT %s]: The context compression finished.",
453             self.name,
454         )
</patched>
</file>