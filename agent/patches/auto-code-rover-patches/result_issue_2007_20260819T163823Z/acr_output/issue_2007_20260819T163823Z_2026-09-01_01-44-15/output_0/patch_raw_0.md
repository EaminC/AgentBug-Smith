The issue is that in the `format_chunk` method, when the chunk_type is "metadata", the usage token counts are swapped. According to Ollama's API docs:

- `prompt_eval_count` refers to the number of tokens in the prompt (input tokens)
- `eval_count` refers to the number of tokens in the response (output tokens)

Currently, `inputTokens` is assigned from `eval_count` (model output tokens) and `outputTokens` from `prompt_eval_count` (input tokens), which is the reverse.

The fix is simply to swap these two assignments in the metadata return dictionary inside the `format_chunk` method's "metadata" case. The `totalTokens` value remains the sum of the two and is fine as is.

No other changes are needed since this directly addresses the reported bug.

---

# modification 1
```
<file>src/strands/models/ollama.py</file>
<original>        case "metadata":
            return {
                "metadata": {
                    "usage": {
                        "inputTokens": event["data"].eval_count,
                        "outputTokens": event["data"].prompt_eval_count,
                        "totalTokens": event["data"].eval_count + event["data"].prompt_eval_count,
                    },
                    "metrics": {
                        "latencyMs": event["data"].total_duration / 1e6,
                    },
                },
            }</original>
<patched>        case "metadata":
            return {
                "metadata": {
                    "usage": {
                        "inputTokens": event["data"].prompt_eval_count,
                        "outputTokens": event["data"].eval_count,
                        "totalTokens": event["data"].eval_count + event["data"].prompt_eval_count,
                    },
                    "metrics": {
                        "latencyMs": event["data"].total_duration / 1e6,
                    },
                },
            }</patched>
```