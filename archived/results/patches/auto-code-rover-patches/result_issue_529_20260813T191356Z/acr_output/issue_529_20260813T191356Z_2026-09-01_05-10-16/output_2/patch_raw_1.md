The main change involves modifying the `Usage` TypedDict in `src/strands/types/event_loop.py` to follow the project pattern of using `Required` and `Optional` from the `typing` module to properly define required and optional fields. Additionally, we add two optional fields, `cacheReadInputTokens` and `cacheWriteInputTokens`, to track the cached token metrics. 

Based on the provided code context, the method `_convert_non_streaming_to_streaming` in `src/strands/models/bedrock.py` already yields a `metadata` event with `usage` data if present in the response. Since the Bedrock API response contains these new cached token fields inside the usage dictionary, they will naturally be propagated if present, because the method yields the entire `response["usage"]` as-is. Therefore, no change is needed there for propagation.

Hence, the only required patch is to update the `Usage` TypedDict declaration.

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
<patched>from typing import Optional, TypedDict, Required

8 class Usage(TypedDict, total=False):
9     """Token usage information for model interactions.
10 
11     Attributes:
12         inputTokens: Number of tokens sent in the request to the model..
13         outputTokens: Number of tokens that the model generated for the request.
14         totalTokens: Total number of tokens (input + output).
15         cacheReadInputTokens: Number of tokens read from cache.
16         cacheWriteInputTokens: Number of tokens written to cache.
17     """
18 
19     inputTokens: Required[int]
20     outputTokens: Required[int]
21     totalTokens: Required[int]
22     cacheReadInputTokens: Optional[int]
23     cacheWriteInputTokens: Optional[int]
</patched>
```