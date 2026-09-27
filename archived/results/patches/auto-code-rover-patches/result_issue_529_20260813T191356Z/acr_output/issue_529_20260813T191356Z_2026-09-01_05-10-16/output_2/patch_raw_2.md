# Reasoning
The main change required is to update the `Usage` TypedDict in `src/strands/types/event_loop.py` to add the two new optional fields for cached tokens, as described in the issue.

Also, in `src/strands/models/bedrock.py`, in the method `_convert_non_streaming_to_streaming`, the existing code simply assigns `response["usage"]` to the metadata event. We should ensure the new cached token metrics fields are preserved here as well. Since the new fields are part of the `usage` dict in the response and are optional, they should simply be included if present. The current code copies the entire `response["usage"]` as-is, so it should include these fields if present. Therefore no code change is needed here unless explicit filtering or transformation is intended.

Because the usage data is directly passed through unchanged, the new cached token fields will be naturally included if present in the response.

Hence the only necessary patch is to update `Usage` TypedDict with `Required` and `Optional` annotations, reflecting the new optional cached token metrics.

---

# Patch

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
from typing_extensions import Required
from typing_extensions import TypedDict


class Usage(TypedDict, total=False):
    """Token usage information for model interactions.

    Attributes:
        inputTokens: Number of tokens sent in the request to the model..
        outputTokens: Number of tokens that the model generated for the request.
        totalTokens: Total number of tokens (input + output).
        cacheReadInputTokens: Tokens read from cache (optional).
        cacheWriteInputTokens: Tokens written to cache (optional).
    """

    inputTokens: Required[int]
    outputTokens: Required[int]
    totalTokens: Required[int]
    cacheReadInputTokens: Optional[int]  # NEW - tokens read from cache
    cacheWriteInputTokens: Optional[int]  # NEW - tokens written to cache
</patched>
```