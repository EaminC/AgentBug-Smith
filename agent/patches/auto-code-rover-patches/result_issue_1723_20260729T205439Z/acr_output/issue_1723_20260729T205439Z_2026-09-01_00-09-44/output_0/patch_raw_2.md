Reasoning:

The problem is that the read cache in `ToolContext` is not cleared when Read tool call blocks are evicted during context compression in the `Agent` class `_split_context_for_compression` and compression process in general.

To fix this, we need to:
1. Add a method in `ToolContext` to clear the read cache entries related to specific file paths.
2. Modify the `Agent.compress_context` method to identify which Read tool call blocks are evicted during the context compression and clear their associated cache entries.

The first is straightforward: add a method to remove cache entries by file paths. This matches the intended behavior in Location #1.

The second requires careful tracking in the `compress_context` method of which tool calls (specifically for Read tools) got removed from the context during compression. After computing the `msgs_to_compress` and `msgs_to_reserve`, we need to find all Read tool call blocks present in the evicted messages (`msgs_to_compress` but not in the reserved ones) and clear their cache entries by invoking the new cache clearing method on the Agent's tool_context.

This preserves the functionality while preventing unbounded memory use caused by stale read cache entries.

---

Patch:

# modification 1: Add method clear_read_cache_for_paths in ToolContext to clear cache entries based on file paths.

```
<file>src/agentscope/state/_state.py</file>
<original>30     read_file_cache: list[ReadCacheEntry] = Field(default_factory=list)
31     """The cache for Read/Write/Edit file tools."""
32 
33     activated_groups: list[str] = Field(default_factory=list)
34     """The names of the activated tool groups, each group contains a set of
35     tools."""
36 
37     async def get_cache(self, file_path: str) -> ReadCacheEntry | None:
38         """Get cached file content if still valid.
39 
40         Args:
41             file_path: The absolute path of the file.
42 
43         Returns:
44             The cached entry if valid, otherwise None.
45         """
46 
47         # Find the cache entry
48         for entry in self.read_file_cache:
49             if entry.file_path == file_path:
50                 # Check if cache is still valid
51                 try:
52                     updated_at = await aiofiles.os.path.getmtime(file_path)
53                     if updated_at == entry.updated_at:
54                         return entry
55                     else:
56                         # Cache is outdated, remove it
57                         self.read_file_cache.remove(entry)
58                         return None
59                 except Exception:
60                     # File might not exist anymore
61                     self.read_file_cache.remove(entry)
62                     return None
63         return None
</original>
<patched>30     read_file_cache: list[ReadCacheEntry] = Field(default_factory=list)
31     """The cache for Read/Write/Edit file tools."""
32 
33     activated_groups: list[str] = Field(default_factory=list)
34     """The names of the activated tool groups, each group contains a set of
35     tools."""
36 
37     async def get_cache(self, file_path: str) -> ReadCacheEntry | None:
38         """Get cached file content if still valid.
39 
40         Args:
41             file_path: The absolute path of the file.
42 
43         Returns:
44             The cached entry if valid, otherwise None.
45         """
46 
47         # Find the cache entry
48         for entry in self.read_file_cache:
49             if entry.file_path == file_path:
50                 # Check if cache is still valid
51                 try:
52                     updated_at = await aiofiles.os.path.getmtime(file_path)
53                     if updated_at == entry.updated_at:
54                         return entry
55                     else:
56                         # Cache is outdated, remove it
57                         self.read_file_cache.remove(entry)
58                         return None
59                 except Exception:
60                     # File might not exist anymore
61                     self.read_file_cache.remove(entry)
62                     return None
63         return None
64 
65     def clear_read_cache_for_paths(self, file_paths: set[str]) -> None:
66         """Clear read_file_cache entries for given file paths."""
67         self.read_file_cache = [
68             entry for entry in self.read_file_cache if entry.file_path not in file_paths
69         ]
</patched>
```

# modification 2: Modify Agent.compress_context to identify evicted Read tool call blocks and clear their associated caches

```
<file>src/agentscope/agent/_agent.py</file>
<original>256     async def compress_context(
257         self,
258         context_config: ContextConfig | None = None,
259     ) -> None:
260         """Compress the agent's context if the token count exceeds the
261         threshold.
262 
263         Args:
264             context_config (`ContextConfig | None`, optional):
265                 If provided, compress the context with the given context
266                 config. Otherwise, use the default context config in the
267                 agent.
268         """
269         cfg: ContextConfig = context_config or self.context_config
270 
271         # Count the current tokens
272         kwargs = await self._prepare_model_input()
273         estimated_tokens = await self.model.count_tokens(**kwargs)
274 
275         # Skip if no compression is needed
276         threshold = cfg.trigger_ratio * self.model.context_size
277         if estimated_tokens < threshold:
278             return
279 
280         logger.info(
281             "[AGENT %s]: Current token count %d exceeds the threshold %d, "
282             "activating compression.",
283             self.name,
284             int(estimated_tokens),
285             int(threshold),
286         )
287 
288         if len(self.state.context) == 0:
289             # The system prompt and the summary (if exists) exceeds the
290             # threshold, which cannot be compressed, raise the error to the
291             # developer!
292             suffix = ""
293             if self.state.summary:
294                 suffix = "and the compression summary "
295             raise RuntimeError(
296                 f"The system prompt {suffix}exceed(s) the compression "
297                 f"threshold ({threshold} tokens), cannot be compressed.",
298             )
299 
300         # Split the context into the ones to be compressed, and the others to
301         # be reserved
302         tools = kwargs.get("tools", [])
303         (
304             msgs_to_compress,
305             msgs_to_reserve,
306         ) = await self._split_context_for_compression(
307             cfg.reserve_ratio * self.model.context_size,
308             tools,
309         )
310 
311         if len(msgs_to_compress) == 0:
312             # The reserve ratio is too large so that although it exceeds the
313             # trigger threshold, the context to be compressed is empty
314             # Fallback by lowering the reserve ratio to compress more context.
315             logger.warning(
316                 "The reserve ratio %.2f is too large to compress any context."
317                 "Lower the reserve ratio to 0 as a fallback.",
318                 cfg.reserve_ratio,
319             )
320             (
321                 msgs_to_compress,
322                 msgs_to_reserve,
323             ) = await self._split_context_for_compression(
324                 0 * self.model.context_size,
325                 tools,
326             )
327 
328             # The msgs to be compressed cannot be empty here, unless the
329             # system prompt and summary (if any) already exceed the context
330             # length, which we have handled before.
331 
332         # Prepare the messages to compress
333         msgs_system = [
334             SystemMsg(
335                 name="system",
336                 content=await self._get_system_prompt(),
337             ),
338         ]
339         if self.state.summary:
340             msgs_system.append(UserMsg("user", self.state.summary))
341 
342         messages = (
343             msgs_system
344             + msgs_to_compress
345             + [
346                 UserMsg(name="user", content=cfg.compression_prompt),
347             ]
348         )
349 
350         # The compression prompt may exceed the context length, here we mark
351         # the overflow by a bool flag
352         compression_tool_schema = [
353             {
354                 "type": "function",
355                 "function": {
356                     "name": "generate_structured_output",
357                     "description": "Call this function to generate "
358                     "structured output required by "
359                     "the user.",
360                     "parameters": cfg.summary_schema,
361                 },
362             },
363         ]
364         context_overflow = False
365         estimated_compression_tokens = await self.model.count_tokens(
366             messages,
367             compression_tool_schema,
368         )
369         if estimated_compression_tokens > self.model.context_size:
370             logger.warning(
371                 "The current context length exceeds the model's context "
372                 "length (%d tokens), the compression maybe failed due to "
373                 "insufficient reserved context for compression.",
374                 self.model.context_size,
375             )
376             context_overflow = True
377 
378         # Compress the messages
379         try:
380             res = await self.model.generate_structured_output(
381                 messages=messages,
382                 structured_model=cfg.summary_schema,
383             )
384 
385         except Exception as e:
386             if context_overflow:
387                 logger.warning(
388                     "Failed to compress context, which may be caused by "
389                     "insufficient reserved context for compression. "
390                     "Trying to compress by removing the oldest context.",
391                 )
392                 for i in range(1, len(msgs_to_compress) + 1):
393                     messages = (
394                         msgs_system
395                         + msgs_to_compress[i:]
396                         + [
397                             UserMsg(
398                                 name="user",
399                                 content=cfg.compression_prompt,
400                             ),
401                         ]
402                     )
403                     estimated_compression_tokens = (
404                         await self.model.count_tokens(
405                             messages,
406                             compression_tool_schema,
407                         )
408                     )
409                     # Considering trigger_ratio <= 0.9, at least reserve 10%
410                     # tokens for compression response
411                     if (
412                         estimated_compression_tokens
413                         < self.model.context_size * cfg.trigger_ratio
414                     ):
415                         break
416 
417                 res = await self.model.generate_structured_output(
418                     messages=messages,
419                     structured_model=cfg.summary_schema,
420                 )
421 
422             else:
423                 raise e from None
424 
425         # Update the summary
426         self.state.summary = cfg.summary_template.format(**res.content)
427 
428         if self.offloader:
429             path = await self.offloader.offload_context(
430                 self.state.session_id,
431                 msgs=msgs_to_compress,
432             )
433 
434             self.state.summary += (
435                 f"\n<system-reminder>The compressed context is offloaded to "
436                 f"'{path}', you can refer to it when needed.</system-reminder>"
437             )
438 
439         # Update the context
440         self.state.context = msgs_to_reserve
441 
442         logger.info(
443             "[AGENT %s]: The context compression finished.",
444             self.name,
445         )</original>
<patched>256     async def compress_context(
257         self,
258         context_config: ContextConfig | None = None,
259     ) -> None:
260         """Compress the agent's context if the token count exceeds the
261         threshold.
262 
263         Args:
264             context_config (`ContextConfig | None`, optional):
265                 If provided, compress the context with the given context
266                 config. Otherwise, use the default context config in the
267                 agent.
268         """
269         cfg: ContextConfig = context_config or self.context_config
270 
271         # Count the current tokens
272         kwargs = await self._prepare_model_input()
273         estimated_tokens = await self.model.count_tokens(**kwargs)
274 
275         # Skip if no compression is needed
276         threshold = cfg.trigger_ratio * self.model.context_size
277         if estimated_tokens < threshold:
278             return
279 
280         logger.info(
281             "[AGENT %s]: Current token count %d exceeds the threshold %d, "
282             "activating compression.",
283             self.name,
284             int(estimated_tokens),
285             int(threshold),
286         )
287 
288         if len(self.state.context) == 0:
289             # The system prompt and the summary (if exists) exceeds the
290             # threshold, which cannot be compressed, raise the error to the
291             # developer!
292             suffix = ""
293             if self.state.summary:
294                 suffix = "and the compression summary "
295             raise RuntimeError(
296                 f"The system prompt {suffix}exceed(s) the compression "
297                 f"threshold ({threshold} tokens), cannot be compressed.",
298             )
299 
300         # Split the context into the ones to be compressed, and the others to
301         # be reserved
302         tools = kwargs.get("tools", [])
303         (
304             msgs_to_compress,
305             msgs_to_reserve,
306         ) = await self._split_context_for_compression(
307             cfg.reserve_ratio * self.model.context_size,
308             tools,
309         )
310 
311         if len(msgs_to_compress) == 0:
312             # The reserve ratio is too large so that although it exceeds the
313             # trigger threshold, the context to be compressed is empty
314             # Fallback by lowering the reserve ratio to compress more context.
315             logger.warning(
316                 "The reserve ratio %.2f is too large to compress any context."
317                 "Lower the reserve ratio to 0 as a fallback.",
318                 cfg.reserve_ratio,
319             )
320             (
321                 msgs_to_compress,
322                 msgs_to_reserve,
323             ) = await self._split_context_for_compression(
324                 0 * self.model.context_size,
325                 tools,
326             )
327 
328             # The msgs to be compressed cannot be empty here, unless the
329             # system prompt and summary (if any) already exceed the context
330             # length, which we have handled before.
331 
332         # Prepare the messages to compress
333         msgs_system = [
334             SystemMsg(
335                 name="system",
336                 content=await self._get_system_prompt(),
337             ),
338         ]
339         if self.state.summary:
340             msgs_system.append(UserMsg("user", self.state.summary))
341 
342         messages = (
343             msgs_system
344             + msgs_to_compress
345             + [
346                 UserMsg(name="user", content=cfg.compression_prompt),
347             ]
348         )
349 
350         # The compression prompt may exceed the context length, here we mark
351         # the overflow by a bool flag
352         compression_tool_schema = [
353             {
354                 "type": "function",
355                 "function": {
356                     "name": "generate_structured_output",
357                     "description": "Call this function to generate "
358                     "structured output required by "
359                     "the user.",
360                     "parameters": cfg.summary_schema,
361                 },
362             },
363         ]
364         context_overflow = False
365         estimated_compression_tokens = await self.model.count_tokens(
366             messages,
367             compression_tool_schema,
368         )
369         if estimated_compression_tokens > self.model.context_size:
370             logger.warning(
371                 "The current context length exceeds the model's context "
372                 "length (%d tokens), the compression maybe failed due to "
373                 "insufficient reserved context for compression.",
374                 self.model.context_size,
375             )
376             context_overflow = True
377 
378         # Compress the messages
379         try:
380             res = await self.model.generate_structured_output(
381                 messages=messages,
382                 structured_model=cfg.summary_schema,
383             )
384 
385         except Exception as e:
386             if context_overflow:
387                 logger.warning(
388                     "Failed to compress context, which may be caused by "
389                     "insufficient reserved context for compression. "
390                     "Trying to compress by removing the oldest context.",
391                 )
392                 for i in range(1, len(msgs_to_compress) + 1):
393                     messages = (
394                         msgs_system
395                         + msgs_to_compress[i:]
396                         + [
397                             UserMsg(
398                                 name="user",
399                                 content=cfg.compression_prompt,
400                             ),
401                         ]
402                     )
403                     estimated_compression_tokens = (
404                         await self.model.count_tokens(
405                             messages,
406                             compression_tool_schema,
407                         )
408                     )
409                     # Considering trigger_ratio <= 0.9, at least reserve 10%
410                     # tokens for compression response
411                     if (
412                         estimated_compression_tokens
413                         < self.model.context_size * cfg.trigger_ratio
414                     ):
415                         break
416 
417                 res = await self.model.generate_structured_output(
418                     messages=messages,
419                     structured_model=cfg.summary_schema,
420                 )
421 
422             else:
423                 raise e from None
424 
425         # Update the summary
426         self.state.summary = cfg.summary_template.format(**res.content)
427 
428         if self.offloader:
429             path = await self.offloader.offload_context(
430                 self.state.session_id,
431                 msgs=msgs_to_compress,
432             )
433 
434             self.state.summary += (
435                 f"\n<system-reminder>The compressed context is offloaded to "
436                 f"'{path}', you can refer to it when needed.</system-reminder>"
437             )
438 
439         # Identify evicted Read tool call blocks and clear their cache
440         # Evicted blocks are those in msgs_to_compress but not in msgs_to_reserve
441         evicted_read_file_paths = set()
442 
443         def extract_read_file_paths(msgs: list[Msg]) -> set[str]:
444             paths = set()
445             for msg in msgs:
446                 for block in msg.get_content_blocks():
447                     # Only consider ToolCallBlock with tool type "Read"
448                     if isinstance(block, ToolCallBlock):
449                         # Retrieve the tool instance by name
450                         tool = self.toolkit.get_tool(block.name)
451                         # Note: get_tool is async, but here we only have sync context,
452                         # so we need to call it async and bridge the gap:
453                         # Solution: run async method get_tool synchronously via asyncio.run() or similar.
454                         # But since compress_context is async, we can move this outside and use async comprehension, easier.
455                         # Instead, gather all block names and fetch tools once async.
456                         # To avoid complexity, will define async internal helper below.
457                         # So instead, gather all tool_call blocks with name "Read" here;
458                         # then later in async part, check their tool type.
459                         # But this approach is complex due to nested async.
460                         # Alternative: we collect all Read tool call blocks first and then filter with async calls.
461                         # We'll implement this logic below.
462 
463         # We must reconsider