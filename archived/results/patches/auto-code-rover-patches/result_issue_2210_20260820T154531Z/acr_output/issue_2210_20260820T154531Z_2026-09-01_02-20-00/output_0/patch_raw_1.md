The reasoning for the patch is:

1. Add a new optional boolean field `strict_tools` with an explanatory docstring in `BedrockConfig`.
2. Modify `_format_request` in `BedrockModel` to check if `strict_tools` is True. If so, insert `"strict": True` into each `toolSpec` dictionary.
3. Detect if the model is Anthropic (based on model_id) and if citations are enabled in `additional_request_fields`. If both are true with `strict_tools=True`, issue a warning.
4. Preserve all existing request construction and return the updated request dictionary accordingly.

No changes to other parts of the class or other files are needed based on the requirements.

---

Patch follows:

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
105             strict_tools: If true, adds `"strict": true` to all toolSpec objects to enable strict schema validation.
106         """
107 
108         additional_args: dict[str, Any] | None
109         additional_request_fields: dict[str, Any] | None
110         additional_response_field_paths: list[str] | None
111         cache_prompt: str | None
112         cache_config: CacheConfig | None
113         cache_tools: str | None
114         guardrail_id: str | None
115         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
116         guardrail_stream_processing_mode: Literal["sync", "async"] | None
117         guardrail_version: str | None
118         guardrail_redact_input: bool | None
119         guardrail_redact_input_message: str | None
120         guardrail_redact_output: bool | None
121         guardrail_redact_output_message: str | None
122         guardrail_latest_message: bool | None
123         max_tokens: int | None
124         model_id: str
125         include_tool_result_status: Literal["auto"] | bool | None
126         service_tier: str | None
127         stop_sequences: list[str] | None
128         streaming: bool | None
129         temperature: float | None
130         top_p: float | None
131         strict_tools: bool | None
</patched>
</file>

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
</original>
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
234         import warnings
235         logger = self.logger if hasattr(self, "logger") else __import__("logging").getLogger(__name__)
236 
237         if not tool_specs:
238             has_tool_content = any(
239                 any("toolUse" in block or "toolResult" in block for block in msg.get("content", [])) for msg in messages
240             )
241             if has_tool_content:
242                 tool_specs = [noop_tool.tool_spec]
243 
244         # Use system_prompt_content directly (copy for mutability)
245         system_blocks: list[SystemContentBlock] = system_prompt_content.copy() if system_prompt_content else []
246         # Add cache point if configured (backwards compatibility)
247         if cache_prompt := self.config.get("cache_prompt"):
248             warnings.warn(
249                 "cache_prompt is deprecated. Use SystemContentBlock with cachePoint instead.", UserWarning, stacklevel=3
250             )
251             system_blocks.append({"cachePoint": {"type": cache_prompt}})
252 
253         strict_on_tools = self.config.get("strict_tools")
254 
255         # Check if citations enabled alongside strict_tools on Anthropic models
256         if strict_on_tools:
257             # Detect if the model is Anthropic via model id substring (case insensitive)
258             model_id_lower = self.config.get("model_id", "").lower()
259             is_anthropic = "anthropic" in model_id_lower or "claude" in model_id_lower
260             # Check if citations enabled in additional_request_fields.docs.document.citations.enabled
261             # We only check if additional_request_fields exists, then check nested keys safely
262             citations_enabled = False
263             additional_fields = self.config.get("additional_request_fields") or {}
264             docs = additional_fields.get("docs") if isinstance(additional_fields, dict) else None
265             document = docs.get("document") if isinstance(docs, dict) else None
266             citations = document.get("citations") if isinstance(document, dict) else None
267             if isinstance(citations, dict):
268                 citations_enabled = citations.get("enabled", False) is True
269 
270             if is_anthropic and citations_enabled:
271                 warnings.warn(
272                     "Bedrock structured outputs with strict_tools enabled are incompatible with citations for Anthropic models. "
273                     "Please disable either `strict_tools` or citations in additional_request_fields.",
274                     stacklevel=3,
275                 )
276 
277         tools_list = []
278         if tool_specs:
279             for tool_spec in tool_specs:
280                 tool_spec_dict = {
281                     "name": tool_spec["name"],
282                     "description": tool_spec["description"],
283                     "inputSchema": tool_spec["inputSchema"],
284                 }
285                 if strict_on_tools:
286                     tool_spec_dict["strict"] = True
287                 tools_list.append({"toolSpec": tool_spec_dict})
288 
289         if self.config.get("cache_tools"):
290             tools_list.append({"cachePoint": {"type": self.config["cache_tools"]}})
291 
292         return {
293             "modelId": self.config["model_id"],
294             "messages": self._format_bedrock_messages(messages),
295             "system": system_blocks,
296             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
297             **(
298                 {
299                     "toolConfig": {
300                         "tools": tools_list,
301                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
302                     }
303                 }
304                 if tool_specs
305                 else {}
306             ),
307             **(self._get_additional_request_fields(tool_choice)),
308             **(
309                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
310                 if self.config.get("additional_response_field_paths")
311                 else {}
312             ),
313             **(
314                 {
315                     "guardrailConfig": {
316                         "guardrailIdentifier": self.config["guardrail_id"],
317                         "guardrailVersion": self.config["guardrail_version"],
318                         "trace": self.config.get("guardrail_trace", "enabled"),
319                         **(
320                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
321                             if self.config.get("guardrail_stream_processing_mode")
322                             else {}
323                         ),
324                     }
325                 }
326                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
327                 else {}
328             ),
329             "inferenceConfig": {
330                 key: value
331                 for key, value in [
332                     ("maxTokens", self.config.get("max_tokens")),
333                     ("temperature", self.config.get("temperature")),
334                     ("topP", self.config.get("top_p")),
335                     ("stopSequences", self.config.get("stop_sequences")),
336                 ]
337                 if value is not None
338             },
339             **(
340                 self.config["additional_args"]
341                 if "additional_args" in self.config and self.config["additional_args"] is not None
342                 else {}
343             ),
344         }
</patched>
</file>
```