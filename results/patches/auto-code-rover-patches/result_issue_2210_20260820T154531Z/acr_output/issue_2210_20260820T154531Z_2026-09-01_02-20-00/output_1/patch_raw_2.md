Reasoning:

We need to add support for a `strict_tools` boolean config in BedrockModel.BedrockConfig; this config enables adding `"strict": True` inside all `toolSpec` objects in the request payload.

Additionally, if `strict_tools=True` is used alongside citations configuration (reported to be incompatible for Anthropic models), we should log a warning.

The key modification is in the `_format_request` method where tool specifications are formatted into `toolConfig["tools"]`. We will add `"strict": True` when `strict_tools` is enabled.

For checking the incompatibility with citations, in Bedrock structured output and docs, citations are indicated in documents under `citations` enabled flag. We don't have direct visibility of citations in the request building but possibly in config or messages. The most straightforward approach is to check if in the config or tool_spec or messages there is usage of citations (we'll assume if config or tool specs or messages contain citations we warn when `strict_tools=True`).

However, given that citations are part of document type content block, and we only have tool specs here, an approximation is to check if the configured citations are set. In our context, the description and the phrasing says "when `strict_tools=True` is used alongside citations configuration" - the existing code snippets suggest that citations appear in content blocks. To minimally implement, we can check if some config related to citations is enabled.

Since the existing `BedrockConfig` doesn't contain a citations flag, to detect citations configuration we can check messages for any citationsContent blocks. But since `_format_request` doesn't take full messages content, only a list of messages we could check for citationsContent in messages and issue a warning accordingly.

But for minimal invasiveness and as per instructions, we can simply log a warning if `strict_tools=True` and if there's any 'citationsContent' present in the messages. So we need to inspect messages to detect whether citations are requested, and if so log.

We will import logging module and use existing logger in the module (`logger` is in existing code).

Summary Changes:
- Add `strict_tools: bool | None` to BedrockConfig with a docstring.
- Update `_format_request` to add `"strict": True` in each toolSpec if `strict_tools=True`.
- Inside `_format_request`, add logic to detect whether citations are requested (check messages for content blocks containing 'citationsContent'), and if so log a warning if strict_tools is enabled.
- Import logging if needed (already imported in this module).
- Preserve existing behaviors.

No changes to test files or other areas required.

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
105             strict_tools: If True, sends "strict": True inside every toolSpec in the request,
106                 enabling schema validation for tool usage to prevent hallucinated tool names and inputs.
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
```

---

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
234         import logging
235         if not tool_specs:
236             has_tool_content = any(
237                 any("toolUse" in block or "toolResult" in block for block in msg.get("content", [])) for msg in messages
238             )
239             if has_tool_content:
240                 tool_specs = [noop_tool.tool_spec]
241 
242         # Use system_prompt_content directly (copy for mutability)
243         system_blocks: list[SystemContentBlock] = system_prompt_content.copy() if system_prompt_content else []
244         # Add cache point if configured (backwards compatibility)
245         if cache_prompt := self.config.get("cache_prompt"):
246             warnings.warn(
247                 "cache_prompt is deprecated. Use SystemContentBlock with cachePoint instead.", UserWarning, stacklevel=3
248             )
249             system_blocks.append({"cachePoint": {"type": cache_prompt}})
250 
251         logger = logging.getLogger(__name__)
252 
253         # Check for citations usage presence in messages for warning
254         has_citations = any(
255             any("citationsContent" in block for block in msg.get("content", []))
256             for msg in messages
257         ) if messages else False
258 
259         if self.config.get("strict_tools") and has_citations:
260             logger.warning(
261                 "Using strict_tools=True with citations is incompatible for Anthropic models; structured outputs and citations may conflict."
262             )
263 
264         return {
265             "modelId": self.config["model_id"],
266             "messages": self._format_bedrock_messages(messages),
267             "system": system_blocks,
268             **({"serviceTier": {"type": self.config["service_tier"]}} if self.config.get("service_tier") else {}),
269             **(
270                 {
271                     "toolConfig": {
272                         "tools": [
273                             *[
274                                 {
275                                     "toolSpec": {
276                                         "name": tool_spec["name"],
277                                         "description": tool_spec["description"],
278                                         "inputSchema": tool_spec["inputSchema"],
279                                         **({"strict": True} if self.config.get("strict_tools") else {}),
280                                     }
281                                 }
282                                 for tool_spec in tool_specs
283                             ],
284                             *(
285                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
286                                 if self.config.get("cache_tools")
287                                 else []
288                             ),
289                         ],
290                         **({"toolChoice": tool_choice if tool_choice else {"auto": {}}}),
291                     }
292                 }
293                 if tool_specs
294                 else {}
295             ),
296             **(self._get_additional_request_fields(tool_choice)),
297             **(
298                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
299                 if self.config.get("additional_response_field_paths")
300                 else {}
301             ),
302             **(
303                 {
304                     "guardrailConfig": {
305                         "guardrailIdentifier": self.config["guardrail_id"],
306                         "guardrailVersion": self.config["guardrail_version"],
307                         "trace": self.config.get("guardrail_trace", "enabled"),
308                         **(
309                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
310                             if self.config.get("guardrail_stream_processing_mode")
311                             else {}
312                         ),
313                     }
314                 }
315                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
316                 else {}
317             ),
318             "inferenceConfig": {
319                 key: value
320                 for key, value in [
321                     ("maxTokens", self.config.get("max_tokens")),
322                     ("temperature", self.config.get("temperature")),
323                     ("topP", self.config.get("top_p")),
324