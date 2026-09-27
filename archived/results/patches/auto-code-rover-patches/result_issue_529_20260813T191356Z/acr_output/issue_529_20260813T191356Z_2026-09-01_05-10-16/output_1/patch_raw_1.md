Reasoning:

To add support for cached token metrics (`cacheReadInputTokens` and `cacheWriteInputTokens`) to the Usage class and the associated usages, we need to:

1. In `src/strands/types/event_loop.py`, extend the Usage TypedDict by making it inherit from `TypedDict` with `total=False` and use `typing_extensions.Required` and `Optional` for correct annotations consistent with the project pattern. Add the two cached token metrics as optional fields.

2. In `src/strands/telemetry/metrics.py` within the `EventLoopMetrics` class, specifically in the `update_usage` method, extend the method to check if the new cached token metrics are present in `usage` and if so, record and accumulate them as well. To do this, we need to initialize those fields with zero in `accumulated_usage`. Thus, we should also update the field initialization of `accumulated_usage` to include these optional fields with default 0 for accumulation.

3. We might need to add metrics recording for these new cached token fields (assuming metrics client has compatible counters), so also add `.record()` calls for those.

4. It's also necessary to update the `get_summary` method's output dictionary to include the new cached token accumulations, so consumers get visibility on them in summaries.

No other files from the provided context need changes since:
- `UsageMetadata` in `models/sagemaker.py` does not clearly show a UsageMetadata usage that we must extend here, and the request is focused on Usage TypedDict in `event_loop.py` and usage in `metrics.py`.
- Adding parsing or streaming logic in SageMaker model streaming is out of scope here (and not indicated as a requirement in the issue description).
  
Hence, the minimal and proper fix is limited to:

- `src/strands/types/event_loop.py`: Extend Usage TypedDict
- `src/strands/telemetry/metrics.py`: Update accumulated_usage initialization and the update_usage method, plus the get_summary to include the new cached usage fields.

---

Patch follows:

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
<patched>from typing import Optional
from typing_extensions import Required, TypedDict

class Usage(TypedDict, total=False):
    """Token usage information for model interactions.

    Attributes:
        inputTokens: Number of tokens sent in the request to the model.
        outputTokens: Number of tokens that the model generated for the request.
        totalTokens: Total number of tokens (input + output).
        cacheReadInputTokens: Tokens read from cache (optional).
        cacheWriteInputTokens: Tokens written to cache (optional).
    """

    inputTokens: Required[int]
    outputTokens: Required[int]
    totalTokens: Required[int]
    cacheReadInputTokens: Optional[int]
    cacheWriteInputTokens: Optional[int]
</patched>
</file>

<file>src/strands/telemetry/metrics.py</file>
<original>171     accumulated_usage: Usage = field(default_factory=lambda: Usage(inputTokens=0, outputTokens=0, totalTokens=0))
...
255     def update_usage(self, usage: Usage) -> None:
256         """Update the accumulated token usage with new usage data.
257 
258         Args:
259             usage: The usage data to add to the accumulated totals.
260         """
261         self._metrics_client.event_loop_input_tokens.record(usage["inputTokens"])
262         self._metrics_client.event_loop_output_tokens.record(usage["outputTokens"])
263         self.accumulated_usage["inputTokens"] += usage["inputTokens"]
264         self.accumulated_usage["outputTokens"] += usage["outputTokens"]
265         self.accumulated_usage["totalTokens"] += usage["totalTokens"]</original>
<patched>171     accumulated_usage: Usage = field(default_factory=lambda: Usage(
172         inputTokens=0,
173         outputTokens=0,
174         totalTokens=0,
175         cacheReadInputTokens=0,
176         cacheWriteInputTokens=0,
177     ))
...
255     def update_usage(self, usage: Usage) -> None:
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
267         # Handle cached token metrics if present
268         if "cacheReadInputTokens" in usage and usage["cacheReadInputTokens"] is not None:
269             self._metrics_client.event_loop_cache_read_input_tokens.record(usage["cacheReadInputTokens"])
270             self.accumulated_usage["cacheReadInputTokens"] += usage["cacheReadInputTokens"]
271
272         if "cacheWriteInputTokens" in usage and usage["cacheWriteInputTokens"] is not None:
273             self._metrics_client.event_loop_cache_write_input_tokens.record(usage["cacheWriteInputTokens"])
274             self.accumulated_usage["cacheWriteInputTokens"] += usage["cacheWriteInputTokens"]
</patched>
</file>

<file>src/strands/telemetry/metrics.py</file>
<original>276     def get_summary(self) -> Dict[str, Any]:
277         """Generate a comprehensive summary of all collected metrics.
278 
279         Returns:
280             A dictionary containing summarized metrics data.
281             This includes cycle statistics, tool usage, traces, and accumulated usage information.
282         """
283         summary = {
284             "total_cycles": self.cycle_count,
285             "total_duration": sum(self.cycle_durations),
286             "average_cycle_time": (sum(self.cycle_durations) / self.cycle_count if self.cycle_count > 0 else 0),
287             "tool_usage": {
288                 tool_name: {
289                     "tool_info": {
290                         "tool_use_id": metrics.tool.get("toolUseId", "N/A"),
291                         "name": metrics.tool.get("name", "unknown"),
292                         "input_params": metrics.tool.get("input", {}),
293                     },
294                     "execution_stats": {
295                         "call_count": metrics.call_count,
296                         "success_count": metrics.success_count,
297                         "error_count": metrics.error_count,
298                         "total_time": metrics.total_time,
299                         "average_time": (metrics.total_time / metrics.call_count if metrics.call_count > 0 else 0),
300                         "success_rate": (metrics.success_count / metrics.call_count if metrics.call_count > 0 else 0),
301                     },
302                 }
303                 for tool_name, metrics in self.tool_metrics.items()
304             },
305             "traces": [trace.to_dict() for trace in self.traces],
306             "accumulated_usage": self.accumulated_usage,
307             "accumulated_metrics": self.accumulated_metrics,
308         }
309         return summary</original>
<patched>276     def get_summary(self) -> Dict[str, Any]:
277         """Generate a comprehensive summary of all collected metrics.
278 
279         Returns:
280             A dictionary containing summarized metrics data.
281             This includes cycle statistics, tool usage, traces, and accumulated usage information.
282         """
283         summary = {
284             "total_cycles": self.cycle_count,
285             "total_duration": sum(self.cycle_durations),
286             "average_cycle_time": (sum(self.cycle_durations) / self.cycle_count if self.cycle_count > 0 else 0),
287             "tool_usage": {
288                 tool_name: {
289                     "tool_info": {
290                         "tool_use_id": metrics.tool.get("toolUseId", "N/A"),
291                         "name": metrics.tool.get("name", "unknown"),
292                         "input_params": metrics.tool.get("input", {}),
293                     },
294                     "execution_stats": {
295                         "call_count": metrics.call_count,
296                         "success_count": metrics.success_count,
297                         "error_count": metrics.error_count,
298                         "total_time": metrics.total_time,
299                         "average_time": (metrics.total_time / metrics.call_count if metrics.call_count > 0 else 0),
300                         "success_rate": (metrics.success_count / metrics.call_count if metrics.call_count > 0 else 0),
301                     },
302                 }
303                 for tool_name, metrics in self.tool_metrics.items()
304             },
305             "traces": [trace.to_dict() for trace in self.traces],
306             "accumulated_usage": self.accumulated_usage,
307             "accumulated_metrics": self.accumulated_metrics,
308             "cacheReadInputTokens": self.accumulated_usage.get("cacheReadInputTokens", 0),
309             "cacheWriteInputTokens": self.accumulated_usage.get("cacheWriteInputTokens", 0),
310         }
311         return summary
</patched>
</file>
