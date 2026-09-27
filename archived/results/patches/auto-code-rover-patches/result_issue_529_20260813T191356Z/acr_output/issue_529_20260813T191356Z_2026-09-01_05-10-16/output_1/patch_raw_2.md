The key goal is to extend the Usage TypedDict to include the optional cached token fields: `cacheReadInputTokens` and `cacheWriteInputTokens`.

Additionally, in the `EventLoopMetrics.update_usage` method, these optional fields should be handled gracefully: i.e. if those keys exist in the usage dict, record and accumulate them; otherwise, ignore silently to preserve backward compatibility. We should also initialize the accumulated_usage with these fields set to zero, to avoid KeyErrors on first use.

In the provided code snippets, the Usage class in `src/strands/types/event_loop.py` is a TypedDict without the new fields, so we must add the new optional fields using the existing pattern (with `Required` and `Optional`).

In `src/strands/telemetry/metrics.py`, the `EventLoopMetrics` class initializes `accumulated_usage` with only the required fields set; we should extend this to include the new cached token fields initialized to zero.

Also, in the method `update_usage`, we should add logic to handle these optional cached fields: record the metric if present in the incoming usage, and add to the accumulated usage.

No changes are explicitly required in the sagemaker.py files for this patch, because that deals with a different layer where UsageMetadata is involved, but the issue does not mandate patching that, only the Usage TypedDict and telemetry metrics aggregation.

---

Patch:

# modification 1: Update Usage TypedDict in src/strands/types/event_loop.py

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
<patched>8 class Usage(TypedDict, total=False):
9     """Token usage information for model interactions.
10 
11     Attributes:
12         inputTokens: Number of tokens sent in the request to the model..
13         outputTokens: Number of tokens that the model generated for the request.
14         totalTokens: Total number of tokens (input + output).
15         cacheReadInputTokens: Tokens read from cache (optional).
16         cacheWriteInputTokens: Tokens written to cache (optional).
17     """
18 
19     inputTokens: Required[int]
20     outputTokens: Required[int]
21     totalTokens: Required[int]
22     cacheReadInputTokens: Optional[int]
23     cacheWriteInputTokens: Optional[int]
</patched>
```

# modification 2: Update EventLoopMetrics class in src/strands/telemetry/metrics.py to initialize accumulated_usage with new fields

```
<file>src/strands/telemetry/metrics.py</file>
<original>171     accumulated_usage: Usage = field(default_factory=lambda: Usage(inputTokens=0, outputTokens=0, totalTokens=0))
</original>
<patched>171     accumulated_usage: Usage = field(
172         default_factory=lambda: Usage(
173             inputTokens=0,
174             outputTokens=0,
175             totalTokens=0,
176             cacheReadInputTokens=0,
177             cacheWriteInputTokens=0,
178         )
179     )
</patched>
```

# modification 3: Update update_usage method to handle optional cacheReadInputTokens and cacheWriteInputTokens fields

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
267         # Handle optional cached token metrics if present
268         if "cacheReadInputTokens" in usage and usage["cacheReadInputTokens"] is not None:
269             if hasattr(self._metrics_client, "event_loop_cache_read_input_tokens"):
270                 self._metrics_client.event_loop_cache_read_input_tokens.record(usage["cacheReadInputTokens"])
271             self.accumulated_usage["cacheReadInputTokens"] += usage["cacheReadInputTokens"]
272 
273         if "cacheWriteInputTokens" in usage and usage["cacheWriteInputTokens"] is not None:
274             if hasattr(self._metrics_client, "event_loop_cache_write_input_tokens"):
275                 self._metrics_client.event_loop_cache_write_input_tokens.record(usage["cacheWriteInputTokens"])
276             self.accumulated_usage["cacheWriteInputTokens"] += usage["cacheWriteInputTokens"]
</patched>
```

Note: We add checks for the metric client event names for robustness (in case those metrics aren't registered). This does not break backward compatibility and aggregates the new tokens if present.

---

This set of changes satisfies the requirements:

- Adds new optional cached token fields to Usage TypedDict with Required/Optional for backward compatibility

- Updates EventLoopMetrics to accumulate and record those new fields if available

- Backwards compatible since existing usages won't break, and new fields are optional

No other file changes are required for this feature addition per the issue description.