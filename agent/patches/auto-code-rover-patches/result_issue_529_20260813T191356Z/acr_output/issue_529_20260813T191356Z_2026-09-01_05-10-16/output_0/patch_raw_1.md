Reasoning:

1. In `src/strands/types/event_loop.py`, the `Usage` TypedDict currently only has three required fields: `inputTokens`, `outputTokens`, and `totalTokens`. We will extend this TypedDict to include the two optional cached token metrics `cacheReadInputTokens` and `cacheWriteInputTokens` as Optional[int], while keeping the existing fields required, and the total=False to allow optional keys.

2. In `src/strands/models/bedrock.py`, specifically in the method `_convert_non_streaming_to_streaming`, the code yields a `metadata` event that contains the `usage` key copied from `response["usage"]`. To support the new cached token fields, we don't need to explicitly extract fields in this method because the entire `usage` dict is already passed along. Thus, no change is strictly needed here.

3. However, the Usage TypedDict is the authoritative type definition for the `usage` dictionary. Adding the new optional fields improves typing coverage.

4. No other spots need to be changed because the cached token fields are included in Bedrock's response under `usage` field and forwarded without modification.

Hence, the only required change is to augment the Usage TypedDict in `src/strands/types/event_loop.py` accordingly.

---

Patch:

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
<patched>from typing import Optional, TypedDict

class Usage(TypedDict, total=False):
    """Token usage information for model interactions.

    Attributes:
        inputTokens: Number of tokens sent in the request to the model..
        outputTokens: Number of tokens that the model generated for the request.
        totalTokens: Total number of tokens (input + output).
        cacheReadInputTokens: (Optional) Tokens read from cache.
        cacheWriteInputTokens: (Optional) Tokens written to cache.
    """

    inputTokens: int
    outputTokens: int
    totalTokens: int
    cacheReadInputTokens: Optional[int]
    cacheWriteInputTokens: Optional[int]
</patched>
```
