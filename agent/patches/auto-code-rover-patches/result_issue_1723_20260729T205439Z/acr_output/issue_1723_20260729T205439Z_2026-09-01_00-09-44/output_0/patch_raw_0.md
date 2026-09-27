Reasoning:

The issue concerns cache lifecycle management for the read cache associated with Read tool call blocks during context compression. When context compression evicts some blocks from the context, the associated read file cache entries are not cleared, causing unbounded cache growth in memory.

To fix this issue:

1. Add a new method `drop_cache_for_files` in `ToolContext` (in `src/agentscope/state/_state.py`) to clear the read cache entries associated with certain file paths.

2. Modify the agent's `_split_context_for_compression` method (in `src/agentscope/agent/_agent.py`) to identify which Read tool call blocks are evicted (i.e., moved from context to compression) during context compression.

3. After splitting the context into messages to compress vs. reserve, gather all file paths involved in Read tool calls that are evicted and use the `ToolContext.drop_cache_for_files` method to remove their cached entries. This ties the cache lifecycle to the presence of the tool call blocks in the agent's context.

This approach keeps the cache lifecycle consistent and avoids unbounded cache growth.

---

Patch:

# modification 1: add method drop_cache_for_files in ToolContext in src/agentscope/state/_state.py 

```
<file>src/agentscope/state/_state.py</file>
<original>30     read_file_cache: list[ReadCacheEntry] = Field(default_factory=list)
31     """The cache for Read/Write/Edit file tools."""</original>
<patched>30     read_file_cache: list[ReadCacheEntry] = Field(default_factory=list)
31     """The cache for Read/Write/Edit file tools."""

32 
33     def drop_cache_for_files(self, file_paths: set[str]) -> None:
34         """Drop the read file cache entries associated with the given file paths.
35 
36         Args:
37             file_paths (`set[str]`):
38                 The set of file paths whose cache entries should be removed.
39         """
40         self.read_file_cache = [
41             entry for entry in self.read_file_cache if entry.file_path not in file_paths
42         ]
</patched>
```

# modification 2: modify compress_context in src/agentscope/agent/_agent.py to drop cache entries of evicted Read tool call blocks

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
311         # --- New code to drop read file cache for evicted Read tool call files ---
312         from src.agentscope.state._state import ToolContext
313 
314         if isinstance(self.state.tool_context, ToolContext):
315             evicted_file_paths = set()
316 
317             def extract_read_file_paths(msgs: list[Msg]) -> set[str]:
318                 file_paths = set()
319                 for msg in msgs:
320                     for block in msg.get_content_blocks():
321                         # identify Read tool call blocks
322                         if (
323                             isinstance(block, ToolCallBlock)
324                             and block.name == "Read"
325                         ):
326                             # The input is expected to be JSON string containing file_path
327                             try:
328                                 import json
329                                 inp = json.loads(block.input)
330                                 path = inp.get("file_path")
331                                 if path:
332                                     file_paths.add(path)
333                             except Exception:
334                                 # ignore JSON parse error
335                                 pass
336                 return file_paths
337 
338             evicted_file_paths = extract_read_file_paths(msgs_to_compress)
339 
340             # Drop the cache for these evicted file paths
341             self.state.tool_context.drop_cache_for_files(evicted_file_paths)
342 
343         # --------------------------------------------------------------------------
344 
345         if len(msgs_to_compress) == 0:
346             # The reserve ratio is too large so that although it exceeds the
347             # trigger threshold, the context to be compressed is empty
348             # Fallback by lowering the reserve ratio to compress more context.
349             logger.warning(
350                 "The reserve ratio %.2f is too large to compress any context."
351                 "Lower the reserve ratio to 0 as a fallback.",
352                 cfg.reserve_ratio,
353             )
354             (
355                 msgs_to_compress,
356                 msgs_to_reserve,
357             ) = await self._split_context_for_compression(
358                 0 * self.model.context_size,
359                 tools,
360             )
361 
362             # The msgs to be compressed cannot be empty here, unless the
363             # system prompt and summary (if any) already exceed the context
364             # length, which we have handled before.
365 
366         # Prepare the messages to compress
367         msgs_system = [
368             SystemMsg(
369                 name="system",
370                 content=await self._get_system_prompt(),
371             ),
372         ]
373         if self.state.summary:
374             msgs_system.append(UserMsg("user", self.state.summary))
375 
376         messages = (
377             msgs_system
378             + msgs_to_compress
379             + [
380                 UserMsg(name="user", content=cfg.compression_prompt),
381             ]
382         )
383 
384         # The compression prompt may exceed the context length, here we mark
385         # the overflow by a bool flag
386         compression_tool_schema = [
387             {
388                 "type": "function",
389                 "function": {
390                     "name": "generate_structured_output",
391                     "description": "Call this function to generate "
392                     "structured output required by "
393                     "the user.",
394                     "parameters": cfg.summary_schema,
395                 },
396             },
397         ]
398         context_overflow = False
399         estimated_compression_tokens = await self.model.count_tokens(
400             messages,
401             compression_tool_schema,
402         )
403         if estimated_compression_tokens > self.model.context_size:
404             logger.warning(
405                 "The current context length exceeds the model's context "
406                 "length (%d tokens), the compression maybe failed due to "
407                 "insufficient reserved context for compression.",
408                 self.model.context_size,
409             )
410             context_overflow = True
411 
412         # Compress the messages
413         try:
414             res = await self.model.generate_structured_output(
415                 messages=messages,
416                 structured_model=cfg.summary_schema,
417             )
418 
419         except Exception as e:
420             if context_overflow:
421                 logger.warning(
422                     "Failed to compress context, which may be caused by "
423                     "insufficient reserved context for compression. "
424                     "Trying to compress by removing the oldest context.",
425                 )
426                 for i in range(1, len(msgs_to_compress) + 1):
427                     messages = (
428                         msgs_system
429                         + msgs_to_compress[i:]
430                         + [
431                             UserMsg(
432                                 name="user",
433                                 content=cfg.compression_prompt,
434                             ),
435                         ]
436                     )
437                     estimated_compression_tokens = (
438                         await self.model.count_tokens(
439                             messages,
440                             compression_tool_schema,
441                         )
442                     )
443                     # Considering trigger_ratio <= 0.9, at least reserve 10%
444                     # tokens for compression response
445                     if (
446                         estimated_compression_tokens
447                         < self.model.context_size * cfg.trigger_ratio
448                     ):
449                         break
450 
451                 res = await self.model.generate_structured_output(
452                     messages=messages,
453                     structured_model=cfg.summary_schema,
454                 )
455 
456             else:
457                 raise e from None
458 
459         # Update the summary
460         self.state.summary = cfg.summary_template.format(**res.content)
461 
462         if self.offloader:
463             path = await self.offloader.offload_context(
464                 self.state.session_id,
465                 msgs=msgs_to_compress,
466             )
467 
468             self.state.summary += (
469                 f"\n<system-reminder>The compressed context is offloaded to "
470                 f"'{path}', you can refer to it when needed.</system-reminder>"
471             )
472 
473         # Update the context
474         self.state.context = msgs_to_reserve
475 
476         logger.info(
477             "[AGENT %s]: The context compression finished.",
478             self.name,
479         )</patched>
```