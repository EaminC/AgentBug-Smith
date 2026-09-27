Reasoning:
The main changes involve extending the `Usage` TypedDict in `strands/types/event_loop.py` to add the two new optional cached token fields: `cacheReadInputTokens` and `cacheWriteInputTokens`. These are optional since older responses might not have them, thus maintaining backward compatibility.

Secondly, in `src/strands/models/bedrock.py`, the `_convert_non_streaming_to_streaming` method is where the Bedrock response is parsed for non-streaming mode. This is the area that builds the `usage` dict that gets yielded in the `metadata` event. We should extend it to include the new cached token metrics fields if they exist in the response usage dictionary.

No other locations need modification as the Usage TypedDict defines the type, and the BedrockModel's parsing function handles integrating these fields from the Bedrock API response.

No new imports are required because these fields are just optional int fields and no new libraries are necessary.

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
<patched>8 from typing import TypedDict, Required, Optional
9 
10 class Usage(TypedDict, total=False):
11     """Token usage information for model interactions.
12 
13     Attributes:
14         inputTokens: Number of tokens sent in the request to the model.
15         outputTokens: Number of tokens that the model generated for the request.
16         totalTokens: Total number of tokens (input + output).
17         cacheReadInputTokens: Tokens read from the cache (optional).
18         cacheWriteInputTokens: Tokens written to the cache (optional).
19     """
20 
21     inputTokens: Required[int]
22     outputTokens: Required[int]
23     totalTokens: Required[int]
24     cacheReadInputTokens: Optional[int]
25     cacheWriteInputTokens: Optional[int]
</patched>
```

# modification 2
```
<file>src/strands/models/bedrock.py</file>
<original>500     def _convert_non_streaming_to_streaming(self, response: dict[str, Any]) -> Iterable[StreamEvent]:
501         """Convert a non-streaming response to the streaming format.
502 
503         Args:
504             response: The non-streaming response from the Bedrock model.
505 
506         Returns:
507             An iterable of response events in the streaming format.
508         """
509         # Yield messageStart event
510         yield {"messageStart": {"role": response["output"]["message"]["role"]}}
511 
512         # Process content blocks
513         for content in response["output"]["message"]["content"]:
514             # Yield contentBlockStart event if needed
515             if "toolUse" in content:
516                 yield {
517                     "contentBlockStart": {
518                         "start": {
519                             "toolUse": {
520                                 "toolUseId": content["toolUse"]["toolUseId"],
521                                 "name": content["toolUse"]["name"],
522                             }
523                         },
524                     }
525                 }
526 
527                 # For tool use, we need to yield the input as a delta
528                 input_value = json.dumps(content["toolUse"]["input"])
529 
530                 yield {"contentBlockDelta": {"delta": {"toolUse": {"input": input_value}}}}
531             elif "text" in content:
532                 # Then yield the text as a delta
533                 yield {
534                     "contentBlockDelta": {
535                         "delta": {"text": content["text"]},
536                     }
537                 }
538             elif "reasoningContent" in content:
539                 # Then yield the reasoning content as a delta
540                 yield {
541                     "contentBlockDelta": {
542                         "delta": {"reasoningContent": {"text": content["reasoningContent"]["reasoningText"]["text"]}}
543                     }
544                 }
545 
546                 if "signature" in content["reasoningContent"]["reasoningText"]:
547                     yield {
548                         "contentBlockDelta": {
549                             "delta": {
550                                 "reasoningContent": {
551                                     "signature": content["reasoningContent"]["reasoningText"]["signature"]
552                                 }
553                             }
554                         }
555                     }
556 
557             # Yield contentBlockStop event
558             yield {"contentBlockStop": {}}
559 
560         # Yield messageStop event
561         yield {
562             "messageStop": {
563                 "stopReason": response["stopReason"],
564                 "additionalModelResponseFields": response.get("additionalModelResponseFields"),
565             }
566         }
567 
568         # Yield metadata event
569         if "usage" in response or "metrics" in response or "trace" in response:
570             metadata: StreamEvent = {"metadata": {}}
571             if "usage" in response:
572                 metadata["metadata"]["usage"] = response["usage"]
573             if "metrics" in response:
574                 metadata["metadata"]["metrics"] = response["metrics"]
575             if "trace" in response:
576                 metadata["metadata"]["trace"] = response["trace"]
577             yield metadata
</original>
<patched>500     def _convert_non_streaming_to_streaming(self, response: dict[str, Any]) -> Iterable[StreamEvent]:
501         """Convert a non-streaming response to the streaming format.
502 
503         Args:
504             response: The non-streaming response from the Bedrock model.
505 
506         Returns:
507             An iterable of response events in the streaming format.
508         """
509         # Yield messageStart event
510         yield {"messageStart": {"role": response["output"]["message"]["role"]}}
511 
512         # Process content blocks
513         for content in response["output"]["message"]["content"]:
514             # Yield contentBlockStart event if needed
515             if "toolUse" in content:
516                 yield {
517                     "contentBlockStart": {
518                         "start": {
519                             "toolUse": {
520                                 "toolUseId": content["toolUse"]["toolUseId"],
521                                 "name": content["toolUse"]["name"],
522                             }
523                         },
524                     }
525                 }
526 
527                 # For tool use, we need to yield the input as a delta
528                 input_value = json.dumps(content["toolUse"]["input"])
529 
530                 yield {"contentBlockDelta": {"delta": {"toolUse": {"input": input_value}}}}
531             elif "text" in content:
532                 # Then yield the text as a delta
533                 yield {
534                     "contentBlockDelta": {
535                         "delta": {"text": content["text"]},
536                     }
537                 }
538             elif "reasoningContent" in content:
539                 # Then yield the reasoning content as a delta
540                 yield {
541                     "contentBlockDelta": {
542                         "delta": {"reasoningContent": {"text": content["reasoningContent"]["reasoningText"]["text"]}}
543                     }
544                 }
545 
546                 if "signature" in content["reasoningContent"]["reasoningText"]:
547                     yield {
548                         "contentBlockDelta": {
549                             "delta": {
550                                 "reasoningContent": {
551                                     "signature": content["reasoningContent"]["reasoningText"]["signature"]
552                                 }
553                             }
554                         }
555                     }
556 
557             # Yield contentBlockStop event
558             yield {"contentBlockStop": {}}
559 
560         # Yield messageStop event
561         yield {
562             "messageStop": {
563                 "stopReason": response["stopReason"],
564                 "additionalModelResponseFields": response.get("additionalModelResponseFields"),
565             }
566         }
567 
568         # Yield metadata event, enhanced with cached token fields if present
569         if "usage" in response or "metrics" in response or "trace" in response:
570             metadata: StreamEvent = {"metadata": {}}
571             if "usage" in response:
572                 # Make a shallow copy to avoid modifying the original response data
573                 usage_copy = dict(response["usage"])
574                 # Include cacheReadInputTokens if present
575                 if "cacheReadInputTokens" in response["usage"]:
576                     usage_copy["cacheReadInputTokens"] = response["usage"]["cacheReadInputTokens"]
577                 # Include cacheWriteInputTokens if present
578                 if "cacheWriteInputTokens" in response["usage"]:
579                     usage_copy["cacheWriteInputTokens"] = response["usage"]["cacheWriteInputTokens"]
580                 metadata["metadata"]["usage"] = usage_copy
581             if "metrics" in response:
582                 metadata["metadata"]["metrics"] = response["metrics"]
583             if "trace" in response:
584                 metadata["metadata"]["trace"] = response["trace"]
585             yield metadata
</patched>
```