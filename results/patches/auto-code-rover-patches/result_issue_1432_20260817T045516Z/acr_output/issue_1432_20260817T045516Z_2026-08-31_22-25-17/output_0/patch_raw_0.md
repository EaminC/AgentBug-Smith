Reasoning:

1. **Model base class**: Add `cache_strategy: str | None = None` attribute to the base Model class for shared configuration. This may involve adding to constructor or a default attribute or property, but since the Model is abstract and has abstract get_config/update_config, the simplest is to define that all models should accept it in their config and get_config returns it.

2. **BedrockModel / AnthropicModel / LiteLLMModel**:
   - Extend their config TypedDict to include `cache_strategy: str | None`.
   - Ensure the `update_config` and `get_config` handle this new `cache_strategy`.
   - Make sure existing behavior around cachePoint injection and conversion is preserved (Bedrock native pass-through, Anthropic and LiteLLM converting cachePoint to cache_control).
   - For LiteLLM, fix the system message formatting to handle cachePoint blocks appropriately to support the automatic caching.

3. **Agent**:
   - After initializing `self.model`, check if `model.get_config().get("cache_strategy") == "auto"` and add the ConversationCachingHook automatically.
   - This automates the hook registration for caching.

4. No changes are required in the streaming methods—they already handle the cachePoint / cache_control conversions internally depending on provider.

Let's make a minimal patch with:

- Add `cache_strategy` to all three model configs.
- Modify Agent `__init__` to add the hook on `cache_strategy == "auto"`.
- Fix LiteLLMModel's `_format_system_messages` to handle cachePoint blocks at message level, injecting `cache_control` properly.

No other behavior needs changes or new imports.

---

Patch:

```
<file>src/strands/models/model.py</file>
<original>19 class Model(abc.ABC):
20     """Abstract base class for Agent model providers.
21 
22     This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
23     standardized way to configure and process requests for different AI model providers.
24     """
25 
26     @abc.abstractmethod
27     # pragma: no cover
28     def update_config(self, **model_config: Any) -> None:
29         """Update the model configuration with the provided arguments.
30 
31         Args:
32             **model_config: Configuration overrides.
33         """
34         pass
35 
36     @abc.abstractmethod
37     # pragma: no cover
38     def get_config(self) -> Any:
39         """Return the model configuration.
40 
41         Returns:
42             The model's configuration.
43         """
44         pass
45 
46     @abc.abstractmethod
47     # pragma: no cover
48     def structured_output(
49         self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
50     ) -> AsyncGenerator[dict[str, T | Any], None]:
51         """Get structured output from the model.
52 
53         Args:
54             output_model: The output model to use for the agent.
55             prompt: The prompt messages to use for the agent.
56             system_prompt: System prompt to provide context to the model.
57             **kwargs: Additional keyword arguments for future extensibility.
58 
59         Yields:
60             Model events with the last being the structured output.
61 
62         Raises:
63             ValidationException: The response format from the model does not match the output_model
64         """
65         pass
66 
67     @abc.abstractmethod
68     # pragma: no cover
69     def stream(
70         self,
71         messages: Messages,
72         tool_specs: list[ToolSpec] | None = None,
73         system_prompt: str | None = None,
74         *,
75         tool_choice: ToolChoice | None = None,
76         system_prompt_content: list[SystemContentBlock] | None = None,
77         invocation_state: dict[str, Any] | None = None,
78         **kwargs: Any,
79     ) -> AsyncIterable[StreamEvent]:
80         """Stream conversation with the model.
81 
82         This method handles the full lifecycle of conversing with the model:
83 
84         1. Format the messages, tool specs, and configuration into a streaming request
85         2. Send the request to the model
86         3. Yield the formatted message chunks
87 
88         Args:
89             messages: List of message objects to be processed by the model.
90             tool_specs: List of tool specifications to make available to the model.
91             system_prompt: System prompt to provide context to the model.
92             tool_choice: Selection strategy for tool invocation.
93             system_prompt_content: System prompt content blocks for advanced features like caching.
94             invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
95             **kwargs: Additional keyword arguments for future extensibility.
96 
97         Yields:
98             Formatted message chunks from the model.
99 
100         Raises:
101             ModelThrottledException: When the model service is throttling requests from the client.
102         """
103         pass
</original>
<patched>19 from typing import Optional
20 
21 class Model(abc.ABC):
22     """Abstract base class for Agent model providers.
23 
24     This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
25     standardized way to configure and process requests for different AI model providers.
26 
27     Attributes:
28         cache_strategy: Optional string indicating cache strategy, e.g., "auto"
29     """
30 
31     cache_strategy: Optional[str] = None  # New attribute for caching strategy
32 
33     @abc.abstractmethod
34     # pragma: no cover
35     def update_config(self, **model_config: Any) -> None:
36         """Update the model configuration with the provided arguments.
37 
38         Args:
39             **model_config: Configuration overrides.
40         """
41         pass
42 
43     @abc.abstractmethod
44     # pragma: no cover
45     def get_config(self) -> Any:
46         """Return the model configuration.
47 
48         Returns:
49             The model's configuration.
50         """
51         pass
52 
53     @abc.abstractmethod
54     # pragma: no cover
55     def structured_output(
56         self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
57     ) -> AsyncGenerator[dict[str, T | Any], None]:
58         """Get structured output from the model.
59 
60         Args:
61             output_model: The output model to use for the agent.
62             prompt: The prompt messages to use for the agent.
63             system_prompt: System prompt to provide context to the model.
64             **kwargs: Additional keyword arguments for future extensibility.
65 
66         Yields:
67             Model events with the last being the structured output.
68 
69         Raises:
70             ValidationException: The response format from the model does not match the output_model
71         """
72         pass
73 
74     @abc.abstractmethod
75     # pragma: no cover
76     def stream(
77         self,
78         messages: Messages,
79         tool_specs: list[ToolSpec] | None = None,
80         system_prompt: str | None = None,
81         *,
82         tool_choice: ToolChoice | None = None,
83         system_prompt_content: list[SystemContentBlock] | None = None,
84         invocation_state: dict[str, Any] | None = None,
85         **kwargs: Any,
86     ) -> AsyncIterable[StreamEvent]:
87         """Stream conversation with the model.
88 
89         This method handles the full lifecycle of conversing with the model:
90 
91         1. Format the messages, tool specs, and configuration into a streaming request
92         2. Send the request to the model
93         3. Yield the formatted message chunks
94 
95         Args:
96             messages: List of message objects to be processed by the model.
97             tool_specs: List of tool specifications to make available to the model.
98             system_prompt: System prompt to provide context to the model.
99             tool_choice: Selection strategy for tool invocation.
100             system_prompt_content: System prompt content blocks for advanced features like caching.
101             invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
102             **kwargs: Additional keyword arguments for future extensibility.
103 
104         Yields:
105             Formatted message chunks from the model.
106 
107         Raises:
108             ModelThrottledException: When the model service is throttling requests from the client.
109         """
110         pass
</patched>
</file>

```

```
<file>src/strands/agent/agent.py</file>
<original>179         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
180         self.messages = messages if messages is not None else []
181         # initializing self._system_prompt for backwards compatibility
182         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
183         self._default_structured_output_model = structured_output_model
184         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
185         self.name = name or _DEFAULT_AGENT_NAME
186         self.description = description
</original>
<patched>179         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
180         self.messages = messages if messages is not None else []
181         # initializing self._system_prompt for backwards compatibility
182         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
183         self._default_structured_output_model = structured_output_model
184         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
185         self.name = name or _DEFAULT_AGENT_NAME
186         self.description = description
187 
188         # Automatic caching hook registration if model has cache_strategy="auto"
189         cache_strategy = None
190         try:
191             cache_strategy = self.model.get_config().get("cache_strategy")  # type: ignore
192         except Exception:
193             cache_strategy = None
194 
195         if cache_strategy == "auto":
196             from strands.agent.cache import ConversationCachingHook
197             self.hooks.add_hook(ConversationCachingHook())
</patched>
</file>

```
<file>src/strands/models/bedrock.py</file>
<original>69     class BedrockConfig(TypedDict, total=False):
70         """Configuration options for Bedrock models.
71 
72         Attributes:
73             additional_args: Any additional arguments to include in the request
74             additional_request_fields: Additional fields to include in the Bedrock request
75             additional_response_field_paths: Additional response field paths to extract
76             cache_prompt: Cache point type for the system prompt
77             cache_tools: Cache point type for tools
78             guardrail_id: ID of the guardrail to apply
79             guardrail_trace: Guardrail trace mode. Defaults to enabled.
80             guardrail_version: Version of the guardrail to apply
81             guardrail_stream_processing_mode: The guardrail processing mode
82             guardrail_redact_input: Flag to redact input if a guardrail is triggered. Defaults to True.
83             guardrail_redact_input_message: If a Bedrock Input guardrail triggers, replace the input with this message.
84             guardrail_redact_output: Flag to redact output if guardrail is triggered. Defaults to False.
85             guardrail_redact_output_message: If a Bedrock Output guardrail triggers, replace output with this message.
86             guardrail_latest_message: Flag to send only the lastest user message to guardrails.
87                 Defaults to False.
88             max_tokens: Maximum number of tokens to generate in the response
89             model_id: The Bedrock model ID (e.g., "us.anthropic.claude-sonnet-4-20250514-v1:0")
90             include_tool_result_status: Flag to include status field in tool results.
91                 True includes status, False removes status, "auto" determines based on model_id. Defaults to "auto".
92             stop_sequences: List of sequences that will stop generation when encountered
93             streaming: Flag to enable/disable streaming. Defaults to True.
94             temperature: Controls randomness in generation (higher = more random)
95             top_p: Controls diversity via nucleus sampling (alternative to temperature)
96         """
97 
98         additional_args: dict[str, Any] | None
99         additional_request_fields: dict[str, Any] | None
100         additional_response_field_paths: list[str] | None
101         cache_prompt: str | None
102         cache_tools: str | None
103         guardrail_id: str | None
104         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
105         guardrail_stream_processing_mode: Literal["sync", "async"] | None
106         guardrail_version: str | None
107         guardrail_redact_input: bool | None
108         guardrail_redact_input_message: str | None
109         guardrail_redact_output: bool | None
110         guardrail_redact_output_message: str | None
111         guardrail_latest_message: bool | None
112         max_tokens: int | None
113         model_id: str
114         include_tool_result_status: Literal["auto"] | bool | None
115         stop_sequences: list[str] | None
116         streaming: bool | None
117         temperature: float | None
118         top_p: float | None
119 </original>
<patched>69     class BedrockConfig(TypedDict, total=False):
70         """Configuration options for Bedrock models.
71 
72         Attributes:
73             additional_args: Any additional arguments to include in the request
74             additional_request_fields: Additional fields to include in the Bedrock request
75             additional_response_field_paths: Additional response field paths to extract
76             cache_prompt: Cache point type for the system prompt
77             cache_tools: Cache point type for tools
78             cache_strategy: Cache strategy for conversation caching (e.g., "auto")
79             guardrail_id: ID of the guardrail to apply
80             guardrail_trace: Guardrail trace mode. Defaults to enabled.
81             guardrail_version: Version of the guardrail to apply
82             guardrail_stream_processing_mode: The guardrail processing mode
83             guardrail_redact_input: Flag to redact input if a guardrail is triggered. Defaults to True.
84             guardrail_redact_input_message: If a Bedrock Input guardrail triggers, replace the input with this message.
85             guardrail_redact_output: Flag to redact output if guardrail is triggered. Defaults to False.
86             guardrail_redact_output_message: If a Bedrock Output guardrail triggers, replace output with this message.
87             guardrail_latest_message: Flag to send only the lastest user message to guardrails.
88                 Defaults to False.
89             max_tokens: Maximum number of tokens to generate in the response
90             model_id: The Bedrock model ID (e.g., "us.anthropic.claude-sonnet-4-20250514-v1:0")
91             include_tool_result_status: Flag to include status field in tool results.
92                 True includes status, False removes status, "auto" determines based on model_id. Defaults to "auto".
93             stop_sequences: List of sequences that will stop generation when encountered
94             streaming: Flag to enable/disable streaming. Defaults to True.
95             temperature: Controls randomness in generation (higher = more random)
96             top_p: Controls diversity via nucleus sampling (alternative to temperature)
97         """
98 
99         additional_args: dict[str, Any] | None
100         additional_request_fields: dict[str, Any] | None
101         additional_response_field_paths: list[str] | None
102         cache_prompt: str | None
103         cache_tools: str | None
104         cache_strategy: str | None
105         guardrail_id: str | None
106         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
107         guardrail_stream_processing_mode: Literal["sync", "async"] | None
108         guardrail_version: str | None
109         guardrail_redact_input: bool | None
110         guardrail_redact_input_message: str | None
111         guardrail_redact_output: bool | None
112         guardrail_redact_output_message: str | None
113         guardrail_latest_message: bool | None
114         max_tokens: int | None
115         model_id: str
116         include_tool_result_status: Literal["auto"] | bool | None
117         stop_sequences: list[str] | None
118         streaming: bool | None
119         temperature: float | None
120         top_p: float | None
</patched>
</file>

```
<file>src/strands/models/bedrock.py</file>
<original>176     def update_config(self, **model_config: Unpack[BedrockConfig]) -> None:  # type: ignore
177         """Update the Bedrock Model configuration with the provided arguments.
178 
179         Args:
180             **model_config: Configuration overrides.
181         """
182         validate_config_keys(model_config, self.BedrockConfig)
183         self.config.update(model_config)
184 
185     @override
186     def get_config(self) -> BedrockConfig:
187         """Get the current Bedrock Model configuration.
188 
189         Returns:
190             The Bedrock model configuration.
191         """
192         return self.config</original>
<patched>176     def update_config(self, **model_config: Unpack[BedrockConfig]) -> None:  # type: ignore
177         """Update the Bedrock Model configuration with the provided arguments.
178 
179         Args:
180             **model_config: Configuration overrides.
181         """
182         validate_config_keys(model_config, self.BedrockConfig)
183         self.config.update(model_config)
184         # Update cache_strategy attribute if present
185         if "cache_strategy" in model_config:
186             self.cache_strategy = model_config["cache_strategy"]
187 
188     @override
189     def get_config(self) -> BedrockConfig:
190         """Get the current Bedrock Model configuration.
191 
192         Returns:
193             The Bedrock model configuration.
194         """
195         return self.config
</patched>
</file>

```
<file>src/strands/models/anthropic.py</file>
<original>49     class AnthropicConfig(TypedDict, total=False):
50         """Configuration options for Anthropic models.
51 
52         Attributes:
53             max_tokens: Maximum number of tokens to generate.
54             model_id: Calude model ID (e.g., "claude-3-7-sonnet-latest").
55                 For a complete list of supported