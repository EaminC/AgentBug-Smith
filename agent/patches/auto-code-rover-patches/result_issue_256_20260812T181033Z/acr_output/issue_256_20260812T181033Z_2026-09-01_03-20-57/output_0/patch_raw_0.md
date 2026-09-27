Reasoning:

The issue requests support for configurable `toolChoice` in the BedrockModel. Currently, it is hard-coded as {"auto": {}} inside the `format_request` method. To support the feature:

1. Add a private instance variable `self._tool_choice` initialized to {"auto": {}} in the `__init__` method.
2. Change the hardcoded `"toolChoice": {"auto": {}}` in `format_request` to use `self._tool_choice`.
3. To support the specific structured output tool usage in `structured_output`, temporarily override `self._tool_choice` with `{"tool": {"name": tool_spec["name"]}}` during the call to `self.stream`, then restore it afterward.

This minimal patch implements the requested configurable toolChoice behavior without modifying other logic, preserving existing streaming and output parsing.

Patch:

```
<file>src/strands/models/bedrock.py</file>
<original>110     def __init__(
111         self,
112         *,
113         boto_session: Optional[boto3.Session] = None,
114         boto_client_config: Optional[BotocoreConfig] = None,
115         region_name: Optional[str] = None,
116         endpoint_url: Optional[str] = None,
117         **model_config: Unpack[BedrockConfig],
118     ):
119         """Initialize provider instance.
120 
121         Args:
122             boto_session: Boto Session to use when calling the Bedrock Model.
123             boto_client_config: Configuration to use when creating the Bedrock-Runtime Boto Client.
124             region_name: AWS region to use for the Bedrock service.
125                 Defaults to the AWS_REGION environment variable if set, or "us-west-2" if not set.
126             endpoint_url: Custom endpoint URL for VPC endpoints (PrivateLink)
127             **model_config: Configuration options for the Bedrock model.
128         """
129         if region_name and boto_session:
130             raise ValueError("Cannot specify both `region_name` and `boto_session`.")
131 
132         self.config = BedrockModel.BedrockConfig(model_id=DEFAULT_BEDROCK_MODEL_ID, include_tool_result_status="auto")
133         self.update_config(**model_config)
134 
135         logger.debug("config=<%s> | initializing", self.config)
136 
137         session = boto_session or boto3.Session()
138 
139         # Add strands-agents to the request user agent
140         if boto_client_config:
141             existing_user_agent = getattr(boto_client_config, "user_agent_extra", None)
142 
143             # Append 'strands-agents' to existing user_agent_extra or set it if not present
144             if existing_user_agent:
145                 new_user_agent = f"{existing_user_agent} strands-agents"
146             else:
147                 new_user_agent = "strands-agents"
148 
149             client_config = boto_client_config.merge(BotocoreConfig(user_agent_extra=new_user_agent))
150         else:
151             client_config = BotocoreConfig(user_agent_extra="strands-agents", read_timeout=DEFAULT_READ_TIMEOUT)
152 
153         resolved_region = region_name or session.region_name or os.environ.get("AWS_REGION") or DEFAULT_BEDROCK_REGION
154 
155         self.client = session.client(
156             service_name="bedrock-runtime",
157             config=client_config,
158             endpoint_url=endpoint_url,
159             region_name=resolved_region,
160         )
161 
162         logger.debug("region=<%s> | bedrock client created", self.client.meta.region_name)
</original>
<patched>110     def __init__(
111         self,
112         *,
113         boto_session: Optional[boto3.Session] = None,
114         boto_client_config: Optional[BotocoreConfig] = None,
115         region_name: Optional[str] = None,
116         endpoint_url: Optional[str] = None,
117         **model_config: Unpack[BedrockConfig],
118     ):
119         """Initialize provider instance.
120 
121         Args:
122             boto_session: Boto Session to use when calling the Bedrock Model.
123             boto_client_config: Configuration to use when creating the Bedrock-Runtime Boto Client.
124             region_name: AWS region to use for the Bedrock service.
125                 Defaults to the AWS_REGION environment variable if set, or "us-west-2" if not set.
126             endpoint_url: Custom endpoint URL for VPC endpoints (PrivateLink)
127             **model_config: Configuration options for the Bedrock model.
128         """
129         if region_name and boto_session:
130             raise ValueError("Cannot specify both `region_name` and `boto_session`.")
131 
132         self.config = BedrockModel.BedrockConfig(model_id=DEFAULT_BEDROCK_MODEL_ID, include_tool_result_status="auto")
133         self.update_config(**model_config)
134 
135         logger.debug("config=<%s> | initializing", self.config)
136 
137         session = boto_session or boto3.Session()
138 
139         # Add strands-agents to the request user agent
140         if boto_client_config:
141             existing_user_agent = getattr(boto_client_config, "user_agent_extra", None)
142 
143             # Append 'strands-agents' to existing user_agent_extra or set it if not present
144             if existing_user_agent:
145                 new_user_agent = f"{existing_user_agent} strands-agents"
146             else:
147                 new_user_agent = "strands-agents"
148 
149             client_config = boto_client_config.merge(BotocoreConfig(user_agent_extra=new_user_agent))
150         else:
151             client_config = BotocoreConfig(user_agent_extra="strands-agents", read_timeout=DEFAULT_READ_TIMEOUT)
152 
153         resolved_region = region_name or session.region_name or os.environ.get("AWS_REGION") or DEFAULT_BEDROCK_REGION
154 
155         self.client = session.client(
156             service_name="bedrock-runtime",
157             config=client_config,
158             endpoint_url=endpoint_url,
159             region_name=resolved_region,
160         )
161 
162         logger.debug("region=<%s> | bedrock client created", self.client.meta.region_name)
163 
164         self._tool_choice = {"auto": {}}  # Add private instance variable to track toolChoice
</patched>
</file>
```

```
<file>src/strands/models/bedrock.py</file>
<original>194     def format_request(
195         self,
196         messages: Messages,
197         tool_specs: Optional[list[ToolSpec]] = None,
198         system_prompt: Optional[str] = None,
199     ) -> dict[str, Any]:
200         """Format a Bedrock converse stream request.
201 
202         Args:
203             messages: List of message objects to be processed by the model.
204             tool_specs: List of tool specifications to make available to the model.
205             system_prompt: System prompt to provide context to the model.
206 
207         Returns:
208             A Bedrock converse stream request.
209         """
210         return {
211             "modelId": self.config["model_id"],
212             "messages": self._format_bedrock_messages(messages),
213             "system": [
214                 *([{"text": system_prompt}] if system_prompt else []),
215                 *([{"cachePoint": {"type": self.config["cache_prompt"]}}] if self.config.get("cache_prompt") else []),
216             ],
217             **(
218                 {
219                     "toolConfig": {
220                         "tools": [
221                             *[{"toolSpec": tool_spec} for tool_spec in tool_specs],
222                             *(
223                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
224                                 if self.config.get("cache_tools")
225                                 else []
226                             ),
227                         ],
228                         "toolChoice": {"auto": {}},
229                     }
230                 }
231                 if tool_specs
232                 else {}
233             ),
234             **(
235                 {"additionalModelRequestFields": self.config["additional_request_fields"]}
236                 if self.config.get("additional_request_fields")
237                 else {}
238             ),
239             **(
240                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
241                 if self.config.get("additional_response_field_paths")
242                 else {}
243             ),
244             **(
245                 {
246                     "guardrailConfig": {
247                         "guardrailIdentifier": self.config["guardrail_id"],
248                         "guardrailVersion": self.config["guardrail_version"],
249                         "trace": self.config.get("guardrail_trace", "enabled"),
250                         **(
251                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
252                             if self.config.get("guardrail_stream_processing_mode")
253                             else {}
254                         ),
255                     }
256                 }
257                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
258                 else {}
259             ),
260             "inferenceConfig": {
261                 key: value
262                 for key, value in [
263                     ("maxTokens", self.config.get("max_tokens")),
264                     ("temperature", self.config.get("temperature")),
265                     ("topP", self.config.get("top_p")),
266                     ("stopSequences", self.config.get("stop_sequences")),
267                 ]
268                 if value is not None
269             },
270             **(
271                 self.config["additional_args"]
272                 if "additional_args" in self.config and self.config["additional_args"] is not None
273                 else {}
274             ),
275         }
</original>
<patched>194     def format_request(
195         self,
196         messages: Messages,
197         tool_specs: Optional[list[ToolSpec]] = None,
198         system_prompt: Optional[str] = None,
199     ) -> dict[str, Any]:
200         """Format a Bedrock converse stream request.
201 
202         Args:
203             messages: List of message objects to be processed by the model.
204             tool_specs: List of tool specifications to make available to the model.
205             system_prompt: System prompt to provide context to the model.
206 
207         Returns:
208             A Bedrock converse stream request.
209         """
210         return {
211             "modelId": self.config["model_id"],
212             "messages": self._format_bedrock_messages(messages),
213             "system": [
214                 *([{"text": system_prompt}] if system_prompt else []),
215                 *([{"cachePoint": {"type": self.config["cache_prompt"]}}] if self.config.get("cache_prompt") else []),
216             ],
217             **(
218                 {
219                     "toolConfig": {
220                         "tools": [
221                             *[{"toolSpec": tool_spec} for tool_spec in tool_specs],
222                             *(
223                                 [{"cachePoint": {"type": self.config["cache_tools"]}}]
224                                 if self.config.get("cache_tools")
225                                 else []
226                             ),
227                         ],
228                         "toolChoice": self._tool_choice,
229                     }
230                 }
231                 if tool_specs
232                 else {}
233             ),
234             **(
235                 {"additionalModelRequestFields": self.config["additional_request_fields"]}
236                 if self.config.get("additional_request_fields")
237                 else {}
238             ),
239             **(
240                 {"additionalModelResponseFieldPaths": self.config["additional_response_field_paths"]}
241                 if self.config.get("additional_response_field_paths")
242                 else {}
243             ),
244             **(
245                 {
246                     "guardrailConfig": {
247                         "guardrailIdentifier": self.config["guardrail_id"],
248                         "guardrailVersion": self.config["guardrail_version"],
249                         "trace": self.config.get("guardrail_trace", "enabled"),
250                         **(
251                             {"streamProcessingMode": self.config.get("guardrail_stream_processing_mode")}
252                             if self.config.get("guardrail_stream_processing_mode")
253                             else {}
254                         ),
255                     }
256                 }
257                 if self.config.get("guardrail_id") and self.config.get("guardrail_version")
258                 else {}
259             ),
260             "inferenceConfig": {
261                 key: value
262                 for key, value in [
263                     ("maxTokens", self.config.get("max_tokens")),
264                     ("temperature", self.config.get("temperature")),
265                     ("topP", self.config.get("top_p")),
266                     ("stopSequences", self.config.get("stop_sequences")),
267                 ]
268                 if value is not None
269             },
270             **(
271                 self.config["additional_args"]
272                 if "additional_args" in self.config and self.config["additional_args"] is not None
273                 else {}
274             ),
275         }
</patched>
</file>
```

```
<file>src/strands/models/bedrock.py</file>
<original>718     async def structured_output(
719         self,
720         output_model: Type[T],
721         prompt: Messages,
722         system_prompt: Optional[str] = None,
723         **kwargs: Any,
724     ) -> AsyncGenerator[dict[str, Union[T, Any]], None]:
725         """Get structured output from the model.
726 
727         Args:
728             output_model: The output model to use for the agent.
729             prompt: The prompt messages to use for the agent.
730             system_prompt: System prompt to provide context to the model.
731             **kwargs: Additional keyword arguments for future extensibility.
732 
733         Yields:
734             Model events with the last being the structured output.
735         """
736         tool_spec = convert_pydantic_to_tool_spec(output_model)
737 
738         response = self.stream(
739             messages=prompt,
740             tool_specs=[tool_spec],
741             system_prompt=system_prompt,
742             **kwargs,
743         )
744         async for event in streaming.process_stream(response):
745             yield event
746 
747         stop_reason, messages, _, _ = event["stop"]
748 
749         if stop_reason != "tool_use":
750             raise ValueError(f'Model returned stop_reason: {stop_reason} instead of "tool_use".')
751 
752         content = messages["content"]
753         output_response: dict[str, Any] | None = None
754         for block in content:
755             # if the tool use name doesn't match the tool spec name, skip, and if the block is not a tool use, skip.
756             # if the tool use name never matches, raise an error.
757             if block.get("toolUse") and block["toolUse"]["name"] == tool_spec["name"]:
758                 output_response = block["toolUse"]["input"]
759             else:
760                 continue
761 
762         if output_response is None:
763             raise ValueError("No valid tool use or tool use input was found in the Bedrock response.")
764 
765         yield {"output": output_model(**output_response)}
</original>
<patched>718     async def structured_output(
719         self,
720         output_model: Type[T],
721         prompt: Messages,
722         system_prompt: Optional[str] = None,
723         **kwargs: Any,
724     ) -> AsyncGenerator[dict[str, Union[T, Any]], None]:
725         """Get structured output from the model.
726 
727         Args:
728             output_model: The output model to use for the agent.
729             prompt: The prompt messages to use for the agent.
730             system_prompt: System prompt to provide context to the model.
731             **kwargs: Additional keyword arguments for future extensibility.
732 
733         Yields:
734             Model events with the last being the structured output.
735         """
736         tool_spec = convert_pydantic_to_tool_spec(output_model)
737 
738         # Temporarily override self._tool_choice for structured output tool
739         temp_tool_choice = self._tool_choice
740         try:
741             self._tool_choice = {"tool": {"name": tool_spec["name"]}}
742             response = self.stream(
743                 messages=prompt,
744                 tool_specs=[tool_spec],
745                 system_prompt=system_prompt,
746                 **kwargs,
747             )
748         finally:
749             self._tool_choice = temp_tool_choice
750 
751         async for event in streaming.process_stream(response):
752             yield event
753 
754         stop_reason, messages, _, _ = event["stop"]
755 
756         if stop_reason != "tool_use":
757             raise ValueError(f'Model returned stop_reason: {stop_reason} instead of "tool_use".')
758 
759         content = messages["content"]
760         output_response: dict[str, Any] | None = None
761         for block in content:
762             # if the tool use name doesn't match the tool spec name, skip, and if the block is not a tool use, skip.
763             # if the tool use name never matches, raise an error.
764             if block.get("toolUse") and block["toolUse"]["name"] == tool_spec["name"]:
765                 output_response = block["toolUse"]["input"]
766             else:
767                 continue
768 
769         if output_response is None:
770             raise ValueError("No valid tool use or tool use input was found in the Bedrock response.")
771 
772         yield {"output": output_model(**output_response)}
</patched>
</file>
```