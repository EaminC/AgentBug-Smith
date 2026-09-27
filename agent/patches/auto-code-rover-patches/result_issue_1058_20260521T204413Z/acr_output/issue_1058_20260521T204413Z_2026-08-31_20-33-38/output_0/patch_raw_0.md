```
<file>src/agentscope/model/_dashscope_model.py</file>
<original>255     async def _parse_dashscope_stream_response(
256         self,
257         start_datetime: datetime,
258         response: Union[
259             AsyncGenerator[GenerationResponse, None],
260             Generator[MultiModalConversationResponse, None, None],
261         ],
262         structured_model: Type[BaseModel] | None = None,
263     ) -> AsyncGenerator[ChatResponse, Any]:
264         """Given a DashScope streaming response generator, extract the content
265             blocks and usages from it and yield ChatResponse objects.
266 
267         Args:
268             start_datetime (`datetime`):
269                 The start datetime of the response generation.
270             response (
271                 `Union[AsyncGenerator[GenerationResponse, None], Generator[ \
272                 MultiModalConversationResponse, None, None]]`
273             ):
274                 DashScope streaming response generator (GenerationResponse or
275                 MultiModalConversationResponse) to parse.
276             structured_model (`Type[BaseModel] | None`, default `None`):
277                 A Pydantic BaseModel class that defines the expected structure
278                 for the model's output.
279 
280         Returns:
281             AsyncGenerator[ChatResponse, Any]:
282                 An async generator that yields ChatResponse objects containing
283                 the content blocks and usage information for each chunk in the
284                 streaming response.
285 
286         .. note::
287             If `structured_model` is not `None`, the expected structured output
288             will be stored in the metadata of the `ChatResponse`.
289         """
290         acc_content, acc_thinking_content = "", ""
291         acc_tool_calls = collections.defaultdict(dict)
292         metadata = None
293 
294         async for chunk in giter(response):
295             if chunk.status_code != HTTPStatus.OK:
296                 raise RuntimeError(
297                     f"Failed to get response from _ API: {chunk}",
298                 )
299 
300             message = chunk.output.choices[0].message
301 
302             # Update reasoning content
303             if isinstance(message.get("reasoning_content"), str):
304                 acc_thinking_content += message["reasoning_content"]
305 
306             # Update text content
307             if isinstance(message.content, str):
308                 acc_content += message.content
309             elif isinstance(message.content, list):
310                 for item in message.content:
311                     if isinstance(item, dict) and "text" in item:
312                         acc_content += item["text"]
313 
314             # Update tool calls
315             for tool_call in message.get("tool_calls", []):
316                 index = tool_call.get("index", 0)
317 
318                 if "id" in tool_call and tool_call["id"] != acc_tool_calls[
319                     index
320                 ].get("id"):
321                     acc_tool_calls[index]["id"] = (
322                         acc_tool_calls[index].get("id", "") + tool_call["id"]
323                     )
324 
325                 if "function" in tool_call:
326                     func = tool_call["function"]
327                     if "name" in func:
328                         acc_tool_calls[index]["name"] = (
329                             acc_tool_calls[index].get("name", "")
330                             + func["name"]
331                         )
332 
333                     if "arguments" in func:
334                         acc_tool_calls[index]["arguments"] = (
335                             acc_tool_calls[index].get("arguments", "")
336                             + func["arguments"]
337                         )
338 
339             # to content blocks
340             content_blocks: list[TextBlock | ToolUseBlock | ThinkingBlock] = []
341             if acc_thinking_content:
342                 content_blocks.append(
343                     ThinkingBlock(
344                         type="thinking",
345                         thinking=acc_thinking_content,
346                     ),
347                 )
348 
349             if acc_content:
350                 content_blocks.append(
351                     TextBlock(
352                         type="text",
353                         text=acc_content,
354                     ),
355                 )
356 
357             for tool_call in acc_tool_calls.values():
358                 repaired_input = _json_loads_with_repair(
359                     tool_call.get("arguments", "{}") or "{}",
360                 )
361 
362                 if not isinstance(repaired_input, dict):
363                     repaired_input = {}
364 
365                 content_blocks.append(
366                     ToolUseBlock(
367                         type="tool_use",
368                         id=tool_call.get("id", ""),
369                         name=tool_call.get("name", ""),
370                         input=repaired_input,
371                     ),
372                 )
373 
374                 if structured_model:
375                     metadata = repaired_input
376 
377             usage = None
378             if chunk.usage:
379                 usage = ChatUsage(
380                     input_tokens=chunk.usage.input_tokens,
381                     output_tokens=chunk.usage.output_tokens,
382                     time=(datetime.now() - start_datetime).total_seconds(),
383                     metadata=chunk.usage,
384                 )
385 
386             parsed_chunk = ChatResponse(
387                 content=content_blocks,
388                 usage=usage,
389                 metadata=metadata,
390             )
391             yield parsed_chunk</original>
<patched>255     async def _parse_dashscope_stream_response(
256         self,
257         start_datetime: datetime,
258         response: Union[
259             AsyncGenerator[GenerationResponse, None],
260             Generator[MultiModalConversationResponse, None, None],
261         ],
262         structured_model: Type[BaseModel] | None = None,
263     ) -> AsyncGenerator[ChatResponse, Any]:
264         """Given a DashScope streaming response generator, extract the content
265             blocks and usages from it and yield ChatResponse objects.
266 
267         Args:
268             start_datetime (`datetime`):
269                 The start datetime of the response generation.
270             response (
271                 `Union[AsyncGenerator[GenerationResponse, None], Generator[ \
272                 MultiModalConversationResponse, None, None]]`
273             ):
274                 DashScope streaming response generator (GenerationResponse or
275                 MultiModalConversationResponse) to parse.
276             structured_model (`Type[BaseModel] | None`, default `None`):
277                 A Pydantic BaseModel class that defines the expected structure
278                 for the model's output.
279 
280         Returns:
281             AsyncGenerator[ChatResponse, Any]:
282                 An async generator that yields ChatResponse objects containing
283                 the content blocks and usage information for each chunk in the
284                 streaming response.
285 
286         .. note::
287             If `structured_model` is not `None`, the expected structured output
288             will be stored in the metadata of the `ChatResponse`.
289         """
290         acc_content, acc_thinking_content = "", ""
291         acc_tool_calls = collections.defaultdict(dict)
292         # New dictionary to buffer tool_call arguments until stream completion signal is received
293         acc_tool_calls_complete = collections.defaultdict(bool)
294         metadata = None
295 
296         async for chunk in giter(response):
297             if chunk.status_code != HTTPStatus.OK:
298                 raise RuntimeError(
299                     f"Failed to get response from _ API: {chunk}",
300                 )
301 
302             message = chunk.output.choices[0].message
303 
304             # Update reasoning content
305             if isinstance(message.get("reasoning_content"), str):
306                 acc_thinking_content += message["reasoning_content"]
307 
308             # Update text content
309             if isinstance(message.content, str):
310                 acc_content += message.content
311             elif isinstance(message.content, list):
312                 for item in message.content:
313                     if isinstance(item, dict) and "text" in item:
314                         acc_content += item["text"]
315 
316             # Update tool calls
317             for tool_call in message.get("tool_calls", []):
318                 index = tool_call.get("index", 0)
319 
320                 if "id" in tool_call and tool_call["id"] != acc_tool_calls[
321                     index
322                 ].get("id"):
323                     acc_tool_calls[index]["id"] = (
324                         acc_tool_calls[index].get("id", "") + tool_call["id"]
325                     )
326 
327                 if "function" in tool_call:
328                     func = tool_call["function"]
329                     if "name" in func:
330                         acc_tool_calls[index]["name"] = (
331                             acc_tool_calls[index].get("name", "")
332                             + func["name"]
333                         )
334 
335                     if "arguments" in func:
336                         acc_tool_calls[index]["arguments"] = (
337                             acc_tool_calls[index].get("arguments", "")
338                             + func["arguments"]
339                         )
340                 # Detect if this chunk indicated the end of streaming for this tool call
341                 if tool_call.get("last", False) is True:
342                     acc_tool_calls_complete[index] = True
343 
344             # to content blocks
345             content_blocks: list[TextBlock | ToolUseBlock | ThinkingBlock] = []
346             if acc_thinking_content:
347                 content_blocks.append(
348                     ThinkingBlock(
349                         type="thinking",
350                         thinking=acc_thinking_content,
351                     ),
352                 )
353 
354             if acc_content:
355                 content_blocks.append(
356                     TextBlock(
357                         type="text",
358                         text=acc_content,
359                     ),
360                 )
361 
362             for index, tool_call in acc_tool_calls.items():
363                 # Only attempt json load with repair if full content received for this tool call
364                 if not acc_tool_calls_complete.get(index, False):
365                     continue
366 
367                 repaired_input = _json_loads_with_repair(
368                     tool_call.get("arguments", "{}") or "{}",
369                 )
370 
371                 if not isinstance(repaired_input, dict):
372                     repaired_input = {}
373 
374                 content_blocks.append(
375                     ToolUseBlock(
376                         type="tool_use",
377                         id=tool_call.get("id", ""),
378                         name=tool_call.get("name", ""),
379                         input=repaired_input,
380                     ),
381                 )
382 
383                 if structured_model:
384                     metadata = repaired_input
385 
386             usage = None
387             if chunk.usage:
388                 usage = ChatUsage(
389                     input_tokens=chunk.usage.input_tokens,
390                     output_tokens=chunk.usage.output_tokens,
391                     time=(datetime.now() - start_datetime).total_seconds(),
392                     metadata=chunk.usage,
393                 )
394 
395             parsed_chunk = ChatResponse(
396                 content=content_blocks,
397                 usage=usage,
398                 metadata=metadata,
399             )
400             yield parsed_chunk
</patched>
```