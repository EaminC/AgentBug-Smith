Reasoning:
The issue requests adding support for cached token metrics `cacheReadInputTokens` and `cacheWriteInputTokens` to the `Usage` TypedDict in `strands/types/event_loop.py` and making sure these metrics are handled when parsing Bedrock model responses in `BedrockModel._convert_non_streaming_to_streaming`.

1. In `strands/types/event_loop.py`, the existing `Usage` TypedDict only contains three required integer attributes (`inputTokens`, `outputTokens`, and `totalTokens`). We need to add two optional integer attributes `cacheReadInputTokens` and `cacheWriteInputTokens` following the existing pattern, using `Required` and `Optional` from `typing_extensions`.

2. In `strands/models/bedrock.py`, within the `_convert_non_streaming_to_streaming` method, the response metadata includes a `"usage"` dictionary. We should ensure that the usage dict includes the cached token fields when they are present in the Bedrock API response and are passed along in the streamed events. The current code passes the response's `usage` dictionary without modification, which is sufficient if the usage dictionary coming from the response contains those keys. So no code change is strictly required here to support the new fields; the current code is already generic and passes the entire usage dictionary along.

3. However, it's safer to verify that the usage dict includes those fields and that their optional presence won't break anything downstream, but since it's just passing the `usage` dictionary as-is, no modification is essential unless the project enforces strict TypedDict checks at runtime. Given the problem statement only explicitly mentions adding those fields to the `Usage` TypedDict, we only need to update the type definition.

Thus, only one code change is necessary: modifying the TypedDict in `strands/types/event_loop.py` by making all fields total=False, use Required for currently required, and add two optional int fields for the cached tokens.

---

Patch:

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
9 from typing_extensions import TypedDict, Required
10 
11 class Usage(TypedDict, total=False):
12     """Token usage information for model interactions.
13 
14     Attributes:
15         inputTokens: Number of tokens sent in the request to the model..
16         outputTokens: Number of tokens that the model generated for the request.
17         totalTokens: Total number of tokens (input + output).
18         cacheReadInputTokens: (Optional) Tokens read from cache
19         cacheWriteInputTokens: (Optional) Tokens written to cache
20     """
21 
22     inputTokens: Required[int]
23     outputTokens: Required[int]
24     totalTokens: Required[int]
25     cacheReadInputTokens: Optional[int]  # NEW - tokens read from cache
26     cacheWriteInputTokens: Optional[int] # NEW - tokens written to cache
</patched>
```