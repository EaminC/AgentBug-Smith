The changes needed to address the issue involve:

1. Extending the `Usage` TypedDict in `src/strands/types/event_loop.py` to include optional fields `cacheReadInputTokens` and `cacheWriteInputTokens`, with appropriate Required and Optional annotations to maintain backward compatibility.

2. Adjusting the `update_usage` method in `src/strands/telemetry/metrics.py` to handle the new cached token metrics fields if present, recording them with the metrics client and accumulating them in `accumulated_usage`.

3. Extending the definition of `UsageMetadata` in `src/strands/models/sagemaker.py` to optionally include `cacheReadInputTokens` and `cacheWriteInputTokens` so that these new token counts are captured in the usage metadata passed through streamed events.

No changes are required for other code locations like streaming parsing because the fields are already passed in usage metadata as dicts and will be accepted if the dataclass is updated properly. Likewise, since the Usage TypedDict is used as a type hint in accumulated_usage and update_usage, extending it there is sufficient.

---

# modification 1
```
<file>src/strands/types/event_loop.py</file>
<original>8 class Usage(TypedDict):
9     """Token usage information for model interactions.
10 
11     Attributes:
12         inputTokens: Number of tokens sent in the request to the model..
13         outputTokens: Number of tokens that the model generated for the request.
14         totalTokens: Total number of tokens (input + output).
15     """
16 
17     inputTokens: int
18     outputTokens: int
19     totalTokens: int
</original>
<patched>8 from typing import Optional
9 from typing_extensions import Required
10 
11 class Usage(TypedDict, total=False):
12     """Token usage information for model interactions.
13 
14     Attributes:
15         inputTokens: Number of tokens sent in the request to the model..
16         outputTokens: Number of tokens that the model generated for the request.
17         totalTokens: Total number of tokens (input + output).
18         cacheReadInputTokens: Optional tokens read from cache.
19         cacheWriteInputTokens: Optional tokens written to cache.
20     """
21 
22     inputTokens: Required[int]
23     outputTokens: Required[int]
24     totalTokens: Required[int]
25     cacheReadInputTokens: Optional[int]
26     cacheWriteInputTokens: Optional[int]
</patched>
```

---

# modification 2
```
<file>src/strands/telemetry/metrics.py</file>
<original>255     def update_usage(self, usage: Usage) -> None:
256         """Update the accumulated token usage with new usage data.
257 
258         Args:
259             usage: The usage data to add to the accumulated totals.
260         """
261         self._metrics_client.event_loop_input_tokens.record(usage["inputTokens"])
262         self._metrics_client.event_loop_output_tokens.record(usage["outputTokens"])
263         self.accumulated_usage["inputTokens"] += usage["inputTokens"]
264         self.accumulated_usage["outputTokens"] += usage["outputTokens"]
265         self.accumulated_usage["totalTokens"] += usage["totalTokens"]
</original>
<patched>255     def update_usage(self, usage: Usage) -> None:
256         """Update the accumulated token usage with new usage data.
257 
258         Args:
259             usage: The usage data to add to the accumulated totals.
260         """
261         self._metrics_client.event_loop_input_tokens.record(usage["inputTokens"])
262         self._metrics_client.event_loop_output_tokens.record(usage["outputTokens"])
263         self.accumulated_usage["inputTokens"] += usage["inputTokens"]
264         self.accumulated_usage["outputTokens"] += usage["outputTokens"]
265         self.accumulated_usage["totalTokens"] += usage["totalTokens"]
266 
267         if "cacheReadInputTokens" in usage and usage["cacheReadInputTokens"] is not None:
268             self._metrics_client.event_loop_cache_read_input_tokens.record(usage["cacheReadInputTokens"])
269             if "cacheReadInputTokens" in self.accumulated_usage:
270                 self.accumulated_usage["cacheReadInputTokens"] += usage["cacheReadInputTokens"]
271             else:
272                 self.accumulated_usage["cacheReadInputTokens"] = usage["cacheReadInputTokens"]
273 
274         if "cacheWriteInputTokens" in usage and usage["cacheWriteInputTokens"] is not None:
275             self._metrics_client.event_loop_cache_write_input_tokens.record(usage["cacheWriteInputTokens"])
276             if "cacheWriteInputTokens" in self.accumulated_usage:
277                 self.accumulated_usage["cacheWriteInputTokens"] += usage["cacheWriteInputTokens"]
278             else:
279                 self.accumulated_usage["cacheWriteInputTokens"] = usage["cacheWriteInputTokens"]
</patched>
```

---

# modification 3
```
<file>src/strands/models/sagemaker.py</file>
<original>26 class UsageMetadata:
27     """Usage metadata for the model.
28 
29     Attributes:
30         total_tokens: Total number of tokens used in the request
31         completion_tokens: Number of tokens used in the completion
32         prompt_tokens: Number of tokens used in the prompt
33         prompt_tokens_details: Additional information about the prompt tokens (optional)
34     """
35 
36     total_tokens: int
37     completion_tokens: int
38     prompt_tokens: int
39     prompt_tokens_details: Optional[int] = 0
</original>
<patched>26 from typing import Optional
27 
28 class UsageMetadata:
29     """Usage metadata for the model.
30 
31     Attributes:
32         total_tokens: Total number of tokens used in the request
33         completion_tokens: Number of tokens used in the completion
34         prompt_tokens: Number of tokens used in the prompt
35         prompt_tokens_details: Additional information about the prompt tokens (optional)
36         cacheReadInputTokens: Optional number of tokens read from cache
37         cacheWriteInputTokens: Optional number of tokens written to cache
38     """
39 
40     total_tokens: int
41     completion_tokens: int
42     prompt_tokens: int
43     prompt_tokens_details: Optional[int] = 0
44     cacheReadInputTokens: Optional[int] = None
45     cacheWriteInputTokens: Optional[int] = None
</patched>
```