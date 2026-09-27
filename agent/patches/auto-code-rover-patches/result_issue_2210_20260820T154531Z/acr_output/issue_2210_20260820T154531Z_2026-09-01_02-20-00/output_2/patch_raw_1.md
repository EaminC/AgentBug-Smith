The reasoning for the patch:
1. Add the new `strict_tools: bool | None` field to the `BedrockConfig` TypedDict with a clear docstring, indicating it enables strict schema validation on all tools.
2. Modify the `_format_request` method to inject `"strict": True` into each `toolSpec` dictionary if `strict_tools` is set to True in the config.
3. Add detection logic for whether citations are present in any content blocks of the messages, specifically checking for the `"citationsContent"` field.
4. If `strict_tools` is enabled and citations are present on an Anthropic model (model id contains "anthropic" or "claude"), emit a warning log, per the Bedrock docs indicating incompatibility between structured outputs (strict schema validation) and citations.
5. Keep the rest of the request formatting intact to preserve existing functionality.

No other changes are needed.

---

Patch:

```
<file>src/strands/models/bedrock.py</file>
<original>73     class BedrockConfig(BaseModelConfig, total=False):
74         """Configuration options for Bedrock models.
75 
76         Attributes:
77             additional_args: Any additional arguments to include in the request
78             additional_request_fields: Additional fields to include in the Bedrock request
79             additional_response_field_paths: Additional response field paths to extract
80             cache_prompt: Cache point type for the system prompt (deprecated, use cache_config)
81             cache_config: Configuration for prompt caching. Use CacheConfig(strategy="auto") for automatic caching.
82             cache_tools: Cache point type for tools
83             guardrail_id: ID of the guardrail to apply
84             guardrail_trace: Guardrail trace mode. Defaults to enabled.
85             guardrail_version: Version of the guardrail to apply
86             guardrail_stream_processing_mode: The guardrail processing mode
87             guardrail_redact_input: Flag to redact input if a guardrail is triggered. Defaults to True.
88             guardrail_redact_input_message: If a Bedrock Input guardrail triggers, replace the input with this message.
89             guardrail_redact_output: Flag to redact output if guardrail is triggered. Defaults to False.
90             guardrail_redact_output_message: If a Bedrock Output guardrail triggers, replace output with this message.
91             guardrail_latest_message: Flag to send only the lastest user message to guardrails.
92                 Defaults to False.
93             max_tokens: Maximum number of tokens to generate in the response
94             model_id: The Bedrock model ID (e.g., "global.anthropic.claude-sonnet-4-6")
95             include_tool_result_status: Flag to include status field in tool results.
96                 True includes status, False removes status, "auto" determines based on model_id. Defaults to "auto".
97             service_tier: Service tier for the request, controlling the trade-off between latency and cost.
98                 Valid values: "default" (standard), "priority" (faster, premium), "flex" (cheaper, slower).
99                 Please check https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html for
100                 supported service tiers, models, and regions
101             stop_sequences: List of sequences that will stop generation when encountered
102             streaming: Flag to enable/disable streaming. Defaults to True.
103             temperature: Controls randomness in generation (higher = more random)
104             top_p: Controls diversity via nucleus sampling (alternative to temperature)
105         """
106 
107         additional_args: dict[str, Any] | None
108         additional_request_fields: dict[str, Any] | None
109         additional_response_field_paths: list[str] | None
110         cache_prompt: str | None
111         cache_config: CacheConfig | None
112         cache_tools: str | None
113         guardrail_id: str | None
114         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
115         guardrail_stream_processing_mode: Literal["sync", "async"] | None
116         guardrail_version: str | None
117         guardrail_redact_input: bool | None
118         guardrail_redact_input_message: str | None
119         guardrail_redact_output: bool | None
120         guardrail_redact_output_message: str | None
121         guardrail_latest_message: bool | None
122         max_tokens: int | None
123         model_id: str
124         include_tool_result_status: Literal["auto"] | bool | None
125         service_tier: str | None
126         stop_sequences: list[str] | None
127         streaming: bool | None
128         temperature: float | None
129         top_p: float | None
130 </original>
<patched>73     class BedrockConfig(BaseModelConfig, total=False):
74         """Configuration options for Bedrock models.
75 
76         Attributes:
77             additional_args: Any additional arguments to include in the request
78             additional_request_fields: Additional fields to include in the Bedrock request
79             additional_response_field_paths: Additional response field paths to extract
80             cache_prompt: Cache point type for the system prompt (deprecated, use cache_config)
81             cache_config: Configuration for prompt caching. Use CacheConfig(strategy="auto") for automatic caching.
82             cache_tools: Cache point type for tools
83             guardrail_id: ID of the guardrail to apply
84             guardrail_trace: Guardrail trace mode. Defaults to enabled.
85             guardrail_version: Version of the guardrail to apply
86             guardrail_stream_processing_mode: The guardrail processing mode
87             guardrail_redact_input: Flag to redact input if a guardrail is triggered. Defaults to True.
88             guardrail_redact_input_message: If a Bedrock Input guardrail triggers, replace the input with this message.
89             guardrail_redact_output: Flag to redact output if guardrail is triggered. Defaults to False.
90             guardrail_redact_output_message: If a Bedrock Output guardrail triggers, replace output with this message.
91             guardrail_latest_message: Flag to send only the lastest user message to guardrails.
92                 Defaults to False.
93             max_tokens: Maximum number of tokens to generate in the response
94             model_id: The Bedrock model ID (e.g., "global.anthropic.claude-sonnet-4-6")
95             include_tool_result_status: Flag to include status field in tool results.
96                 True includes status, False removes status, "auto" determines based on model_id. Defaults to "auto".
97             service_tier: Service tier for the request, controlling the trade-off between latency and cost.
98                 Valid values: "default" (standard), "priority" (faster, premium), "flex" (cheaper, slower).
99                 Please check https://docs.aws.amazon.com/bedrock/latest/userguide/service-tiers-inference.html for
100                 supported service tiers, models, and regions
101             stop_sequences: List of sequences that will stop generation when encountered
102             streaming: Flag to enable/disable streaming. Defaults to True.
103             temperature: Controls randomness in generation (higher = more random)
104             top_p: Controls diversity via nucleus sampling (alternative to temperature)
105             strict_tools: Enable strict schema validation on all tools in the request.
106                 When True, each toolSpec in the request will include "strict": True to enforce schema validation.
107                 Defaults to None.
108         """
109 
110         additional_args: dict[str, Any] | None
111         additional_request_fields: dict[str, Any] | None
112         additional_response_field_paths: list[str] | None
113         cache_prompt: str | None
114         cache_config: CacheConfig | None
115         cache_tools: str | None
116         guardrail_id: str | None
117         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
118         guardrail_stream_processing_mode: Literal["sync", "async"] | None
119         guardrail_version: str | None
120         guardrail_redact_input: bool | None
121         guardrail_redact_input_message: str | None
122         guardrail_redact_output: bool | None
123         guardrail_redact_output_message: str | None
124         guardrail_latest_message: bool | None
125         max_tokens: int | None
126         model_id: str
127         include_tool_result_status: Literal["auto"] | bool | None
128         service_tier: str | None
129         stop_sequences: list[str] | None
130         streaming: bool | None
131         temperature: float | None
132         top_p: float | None
133         strict_tools: bool | None
134 </patched>
```

```
<file>src/strands/models/bedrock.py</file>
<original>250         return {
251             "modelId": self.config["model_id"],
252             "messages": self._format_bedrock_messages(messages),
253             "system": system_blocks,
254             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
255             **(
256                 {
257                     "toolConfig": {
258                         "tools": [
259                             *[
260                                 {
261                                     "toolSpec": {
262                                         "name": tool_spec["name"],
263                                         "description": tool_spec["description"],
264                                         "inputSchema": tool_spec["inputSchema"],
265                                     }
266                                 }
267                                 for tool_spec in tool_specs
268                             ],
269                             *(
270                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
271                                 if self.config.get("cache_tools")
272                                 else []
273                             ),
274                         ],
275                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
276                     }
277                 }
278                 if tool_specs
279                 else {}
280             ),
281             **(self._get_additional_request_fields(tool_choice)),
282             **(
283                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
284                 if self.config.get("additional_response_field_paths")
285                 else {}
286             ),
287             **(
288                 {
289                     "guardrailConfig": {
290                         "guardrailIdentifier": self.config["guardrail_id"],
291                         "guardrailVersion": self.config["guardrail_version"],
292                         "trace": self.config.get("guardrail_trace", "enabled"),
293                         **(
294                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
295                             if self.config.get("guardrail_stream_processing_mode")
296                             else {}
297                         ),
298                     }
299                 }
300                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
301                 else {}
302             ),
303             "inferenceConfig": {
304                 key: value
305                 for key, value in [
306                     ("maxTokens", self.config.get("max_tokens")),
307                     ("temperature", self.config.get("temperature")),
308                     ("topP", self.config.get("top_p")),
309                     ("stopSequences", self.config.get("stop_sequences")),
310                 ]
311                 if value is not None
312             },
313             **(
314                 self.config["additional_args"]
315                 if "additional_args" in self.config and self.config["additional_args"] is not None
316                 else {}
317             ),
318         }</original>
<patched>250         # Detect if citations are present in any of the messages content
251         has_citations = any(
252             any("citationsContent" in block for block in msg.get("content", []))
253             for msg in messages
254         )
255 
256         # Log a warning if strict_tools is enabled alongside citations for Anthropic models
257         model_id_lower = self.config["model_id"].lower()
258         if self.config.get("strict_tools") and has_citations and (
259             "anthropic" in model_id_lower or "claude" in model_id_lower
260         ):
261             logger.warning(
262                 "Using strict_tools=True with citations enabled is incompatible with Anthropic models."
263                 " Structured output is incompatible with citations per Bedrock documentation."
264             )
265 
266         return {
267             "modelId": self.config["model_id"],
268             "messages": self._format_bedrock_messages(messages),
269             "system": system_blocks,
270             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
271             **(
272                 {
273                     "toolConfig": {
274                         "tools": [
275                             *[
276                                 {
277                                     "toolSpec": {
278                                         "name": tool_spec["name"],
279                                         "description": tool_spec["description"],
280                                         "inputSchema": tool_spec["inputSchema"],
281                                         **({"strict": True} if self.config.get("strict_tools") else {}),
282                                     }
283                                 }
284                                 for tool_spec in tool_specs
285                             ],
286                             *(
287                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
288                                 if self.config.get("cache_tools")
289                                 else []
290                             ),
291                         ],
292                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
293                     }
294                 }
295                 if tool_specs
296                 else {}
297             ),
298             **(self._get_additional_request_fields(tool_choice)),
299             **(
300                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
301                 if self.config.get("additional_response_field_paths")
302                 else {}
303             ),
304             **(
305                 {
306                     "guardrailConfig": {
307                         "guardrailIdentifier": self.config["guardrail_id"],
308                         "guardrailVersion": self.config["guardrail_version"],
309                         "trace": self.config.get("guardrail_trace", "enabled"),
310                         **(
311                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
312                             if self.config.get("guardrail_stream_processing_mode")
313                             else {}
314                         ),
315                     }
316                 }
317                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
318                 else {}
319             ),
320             "inferenceConfig": {
321                 key: value
322                 for key, value in [
323                     ("maxTokens", self.config.get("max_tokens")),
324                     ("temperature", self.config.get("temperature")),
325                     ("topP", self.config.get("top_p")),
326                     ("stopSequences", self.config.get("stop_sequences")),
327                 ]
328                 if value is not None
329             },
330             **(
331                 self.config["additional_args"]
332                 if "additional_args" in self.config and self.config["additional_args"] is not None
333                 else {}
334             ),
335         }</patched>
```