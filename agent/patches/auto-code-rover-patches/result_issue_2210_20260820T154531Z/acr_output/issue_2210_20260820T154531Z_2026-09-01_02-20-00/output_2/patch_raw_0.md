Reasoning:

To implement the requested feature that adds `strict_tools: bool | None` to the BedrockConfig and injects `"strict": True` into each `toolSpec` in the `_format_request` method when `strict_tools` is enabled, the main focus is:

1. Modify `BedrockConfig` to add the new `strict_tools` field with a clear docstring.
2. Update the `_format_request` method to conditionally insert `"strict": True` into each toolSpec when `strict_tools` is True.
3. Add logic in `_format_request` to detect if `strict_tools` is True and citations are present in the messages or tool_configs for Anthropic models, and if so, emit a warning log.
4. This warning is important because the Bedrock docs mention structured outputs (enabled through strict) is incompatible with citations for Anthropic models.

The only two code locations needing changes are:

- the definition of BedrockConfig (location #1 and #3 overlap here),
- and the `_format_request` method (location #2 and #3 overlap here).

No code changes should break anything else or affect other functionality.

----

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
105             strict_tools: Enables strict schema validation on all tool specifications in the request.
106                 Enabling this setting instructs the model to strictly validate tool names and inputs
107                 according to their defined schemas, preventing hallucinated tool names or invalid inputs.
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
<original>216     def _format_request(
217         self,
218         messages: Messages,
219         tool_specs: list[ToolSpec] | None = None,
220         system_prompt_content: list[SystemContentBlock] | None = None,
221         tool_choice: ToolChoice | None = None,
222     ) -> dict[str, Any]:
223         """Format a Bedrock converse stream request.
224 
225         Args:
226             messages: List of message objects to be processed by the model.
227             tool_specs: List of tool specifications to make available to the model.
228             tool_choice: Selection strategy for tool invocation.
229             system_prompt_content: System prompt content blocks to provide context to the model.
230 
231         Returns:
232             A Bedrock converse stream request.
233         """
234         if not tool_specs:
235             has_tool_content = any(
236                 any("toolUse" in block or "toolResult" in block for block in msg.get("content", [])) for msg in messages
237             )
238             if has_tool_content:
239                 tool_specs = [noop_tool.tool_spec]
240 
241         # Use system_prompt_content directly (copy for mutability)
242         system_blocks: list[SystemContentBlock] = system_prompt_content.copy() if system_prompt_content else []
243         # Add cache point if configured (backwards compatibility)
244         if cache_prompt := self.config.get("cache_prompt"):
245             warnings.warn(
246                 "cache_prompt is deprecated. Use SystemContentBlock with cachePoint instead.", UserWarning, stacklevel=3
247             )
248             system_blocks.append({"cachePoint": {"type": cache_prompt}})
249 
250         return {
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
318         }
319 </original>
<patched>216     def _format_request(
217         self,
218         messages: Messages,
219         tool_specs: list[ToolSpec] | None = None,
220         system_prompt_content: list[SystemContentBlock] | None = None,
221         tool_choice: ToolChoice | None = None,
222     ) -> dict[str, Any]:
223         """Format a Bedrock converse stream request.
224 
225         Args:
226             messages: List of message objects to be processed by the model.
227             tool_specs: List of tool specifications to make available to the model.
228             tool_choice: Selection strategy for tool invocation.
229             system_prompt_content: System prompt content blocks to provide context to the model.
230 
231         Returns:
232             A Bedrock converse stream request.
233         """
234         if not tool_specs:
235             has_tool_content = any(
236                 any("toolUse" in block or "toolResult" in block for block in msg.get("content", [])) for msg in messages
237             )
238             if has_tool_content:
239                 tool_specs = [noop_tool.tool_spec]
240 
241         # Use system_prompt_content directly (copy for mutability)
242         system_blocks: list[SystemContentBlock] = system_prompt_content.copy() if system_prompt_content else []
243         # Add cache point if configured (backwards compatibility)
244         if cache_prompt := self.config.get("cache_prompt"):
245             warnings.warn(
246                 "cache_prompt is deprecated. Use SystemContentBlock with cachePoint instead.", UserWarning, stacklevel=3
247             )
248             system_blocks.append({"cachePoint": {"type": cache_prompt}})
249 
250         # Determine if citations content is present in messages, for incompatibility warning
251         has_citations = any(
252             any("citationsContent" in block for block in msg.get("content", [])) for msg in messages
253         )
254 
255         # Also check documents for citations enabled flag if possible in tool specs or messages, helper to be thorough
256         # But here we'll rely on presence of citationsContent in messages which covers typical use
257 
258         # Log warning if strict_tools and citations present for Anthropic models
259         strict_tools_enabled = self.config.get("strict_tools", False)
260         model_id_lower = self.config.get("model_id", "").lower()
261         is_anthropic = "anthropic" in model_id_lower or "claude" in model_id_lower
262 
263         if strict_tools_enabled and has_citations and is_anthropic:
264             logger.warning(
265                 "Using strict_tools=True in BedrockModel is incompatible with citations for Anthropic models. "
266                 "This may lead to errors or unexpected behavior. Please disable one of these features."
267             )
268 
269         return {
270             "modelId": self.config["model_id"],
271             "messages": self._format_bedrock_messages(messages),
272             "system": system_blocks,
273             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
274             **(
275                 {
276                     "toolConfig": {
277                         "tools": [
278                             *[
279                                 {
280                                     "toolSpec": {
281                                         "name": tool_spec["name"],
282                                         "description": tool_spec["description"],
283                                         "inputSchema": tool_spec["inputSchema"],
284                                         **({"strict": True} if strict_tools_enabled else {}),
285                                     }
286                                 }
287                                 for tool_spec in tool_specs
288                             ],
289                             *(
290                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
291                                 if self.config.get("cache_tools")
292                                 else []
293                             ),
294                         ],
295                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
296                     }
297                 }
298                 if tool_specs
299                 else {}
300             ),
301             **(self._get_additional_request_fields(tool_choice)),
302             **(
303                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
304                 if self.config.get("additional_response_field_paths")
305                 else {}
306             ),
307             **(
308                 {
309                     "guardrailConfig": {
310                         "guardrailIdentifier": self.config["guardrail_id"],
311                         "guardrailVersion": self.config["guardrail_version"],
312                         "trace": self.config.get("guardrail_trace", "enabled"),
313                         **(
314                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
315                             if self.config.get("guardrail_stream_processing_mode")
316                             else {}
317                         ),
318                     }
319                 }
320                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
321                 else {}
322             ),
323             "inferenceConfig": {
324                 key: value
325                 for key, value in [
326                     ("maxTokens", self.config.get("max_tokens")),
327                     ("temperature", self.config.get("temperature")),
328                     ("topP", self.config.get("top_p")),
329                     ("stopSequences", self.config.get("stop_sequences")),
330                 ]
331                 if value is not None
332             },
333             **(
334                 self.config["additional_args"]
335                 if "additional_args" in self.config and self.config["additional_args"] is not None
336                 else {}
337             ),
338         }
339 </patched>
```