Reasoning:

The primary need is to extend the Usage TypedDict in `src/strands/types/event_loop.py` to mark existing fields as Required[int] and add two new optional token fields: `cacheReadInputTokens` and `cacheWriteInputTokens`, both Optional[int].

Additionally, from the BedrockModel's method `_convert_non_streaming_to_streaming` in `src/strands/models/bedrock.py`, the usage data is passed as-is in the yielded metadata event. Since the usage data from Bedrock API may now include the new cached tokens keys, no direct change is needed for consuming this data in this method.

No other changes appear necessary since the caller of this usage data and the Usage type itself are the main focus here.

This patch will:

- Update `Usage` TypedDict accordingly.
- Import `Required` and `Optional` from `typing_extensions` as is consistent with the code style mentioned.
- Add new token usage fields as optional.
  

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
<patched>from typing import Optional
from typing_extensions import Required, TypedDict

8 class Usage(TypedDict, total=False):
9     """Token usage information for model interactions.
10 
11     Attributes:
12         inputTokens: Number of tokens sent in the request to the model..
13         outputTokens: Number of tokens that the model generated for the request.
14         totalTokens: Total number of tokens (input + output).
15         cacheReadInputTokens: (Optional) Number of tokens read from cache.
16         cacheWriteInputTokens: (Optional) Number of tokens written to cache.
17     """
18 
19     inputTokens: Required[int]
20     outputTokens: Required[int]
21     totalTokens: Required[int]
22     cacheReadInputTokens: Optional[int]
23     cacheWriteInputTokens: Optional[int]
</patched>
```