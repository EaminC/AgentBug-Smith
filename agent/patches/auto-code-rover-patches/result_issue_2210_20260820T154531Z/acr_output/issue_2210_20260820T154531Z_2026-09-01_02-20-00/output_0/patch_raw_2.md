# Reasoning

1. We add the new `strict_tools` field to the `BedrockConfig` TypedDict with appropriate docstring.
2. In the `_format_request` method of `BedrockModel`, we check if `strict_tools=True` in the config. If so, for each `tool_spec`, we inject `"strict": True` inside the `toolSpec` dictionary.
3. We also check if `strict_tools=True` and citations are enabled in `additional_request_fields` (for `citations` key) for an Anthropic model (model id contains `"anthropic"`). If so, we log a warning about incompatibility.
4. All other behaviors and fields must remain unchanged.

We do not modify `ToolSpec` TypedDict as requested, nor other unrelated logic.

# Patch

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
</original>
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
105             strict_tools: Optional boolean to enable `"strict": true` on all toolSpec entries for request-level tool strictness.
106                 Enables Bedrock schema validation to prevent hallucinated tool names or inputs.
107         """
108 
109         additional_args: dict[str, Any] | None
110         additional_request_fields: dict[str, Any] | None
111         additional_response_field_paths: list[str] | None
112         cache_prompt: str | None
113         cache_config: CacheConfig | None
114         cache_tools: str | None
115         guardrail_id: str | None
116         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
117         guardrail_stream_processing_mode: Literal["sync", "async"] | None
118         guardrail_version: str | None
119         guardrail_redact_input: bool | None
120         guardrail_redact_input_message: str | None
121         guardrail_redact_output: bool | None
122         guardrail_redact_output_message: str | None
123         guardrail_latest_message: bool | None
124         max_tokens: int | None
125         model_id: str
126         include_tool_result_status: Literal["auto"] | bool | None
127         service_tier: str | None
128         stop_sequences: list[str] | None
129         streaming: bool | None
130         temperature: float | None
131         top_p: float | None
132         strict_tools: bool | None
</patched>
</file>


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
<patched>250         import warnings
251 
252         if (
253             self.config.get("strict_tools")
254             and self.config.get("additional_request_fields")
255             and "citations" in self.config["additional_request_fields"]
256             and "anthropic" in self.config.get("model_id", "").lower()
257         ):
258             warnings.warn(
259                 "strict_tools=True is incompatible with citations enabled for Anthropic models per Bedrock docs.",
260                 stacklevel=3,
261             )
262 
263         tool_list: list[dict[str, Any]] = []
264         if tool_specs:
265             for tool_spec in tool_specs:
266                 tool_spec_dict = {
267                     "name": tool_spec["name"],
268                     "description": tool_spec["description"],
269                     "inputSchema": tool_spec["inputSchema"],
270                 }
271                 if self.config.get("strict_tools"):
272                     tool_spec_dict["strict"] = True
273                 tool_list.append({"toolSpec": tool_spec_dict})
274 
275             if self.config.get("cache_tools"):
276                 tool_list.append({"cachePoint": {"type": self.config["cache_tools"]}})
277         else:
278             tool_list = []
279 
280         return {
281             "modelId": self.config["model_id"],
282             "messages": self._format_bedrock_messages(messages),
283             "system": system_blocks,
284             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
285             **(
286                 {
287                     "toolConfig": {
288                         "tools": tool_list,
289                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
290                     }
291                 }
292                 if tool_list
293                 else {}
294             ),
295             **(self._get_additional_request_fields(tool_choice)),
296             **(
297                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
298                 if self.config.get("additional_response_field_paths")
299                 else {}
300             ),
301             **(
302                 {
303                     "guardrailConfig": {
304                         "guardrailIdentifier": self.config["guardrail_id"],
305                         "guardrailVersion": self.config["guardrail_version"],
306                         "trace": self.config.get("guardrail_trace", "enabled"),
307                         **(
308                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
309                             if self.config.get("guardrail_stream_processing_mode")
310                             else {}
311                         ),
312                     }
313                 }
314                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
315                 else {}
316             ),
317             "inferenceConfig": {
318                 key: value
319                 for key, value in [
320                     ("maxTokens", self.config.get("max_tokens")),
321                     ("temperature", self.config.get("temperature")),
322                     ("topP", self.config.get("top_p")),
323                     ("stopSequences", self.config.get("stop_sequences")),
324                 ]
325                 if value is not None
326             },
327             **(
328                 self.config["additional_args"]
329                 if "additional_args" in self.config and self.config["additional_args"] is not None
330                 else {}
331             ),
332         }
</patched>
</file>
```