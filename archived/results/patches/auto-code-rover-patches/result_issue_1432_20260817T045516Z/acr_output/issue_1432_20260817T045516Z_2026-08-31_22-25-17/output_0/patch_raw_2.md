Reasoning:

1. **Model Base Class**: We need to add `cache_strategy: Optional[str] = None` to the base Model configuration. Since the base Model class is abstract and does not have explicit config attributes or constructor, the best approach is to update docstrings and ensure get_config implementations include this config field in derived classes. However, since the base class does not have a constructor, we just add a `cache_strategy` attribute definition and hint it should be part of the model's config to propagate to all providers.

2. **Agent class (agent.py)**: After self.model is initialized (lines near 179), add a check for the cache_strategy property in `self.model.get_config()`. If `cache_strategy == "auto"`, add the `ConversationCachingHook()` to `self.hooks`. This enables the automatic registration of caching hooks.

3. **Model providers**:
    - **BedrockModel**: Add `cache_strategy` to the BedrockConfig TypedDict, update `update_config` and `get_config` to handle this new field, passing it through unchanged. For handling injected cachePoint blocks, Bedrock already supports pass-through of these; no logic changes needed but the config must propagate.
    - **AnthropicModel**: Add `cache_strategy` to AnthropicConfig. In message formatting, Anthropic converts `cachePoint` blocks to `cache_control: {"type": "ephemeral"}` already. No direct handling of cache_strategy for prompt injection needed here; just config propagation.
    - **LiteLLMModel**: Add `cache_strategy` to LiteLLMConfig. Fix system message formatting (the `_format_system_messages` class method) for `cachePoint` blocks: if a `cachePoint` with type "default" is found, apply a cache_control marker to the immediately preceding content block's dictionary to support prompt caching at message level. This matches the proposed "fix needed" in the issue description and resolves cache handling for LiteLLM provider.

4. **ConversationCachingHook**: Not provided in the snippets, but the issue states that when cache_strategy is "auto", Agent registers the hook which injects cachePoint blocks at last assistant message.

These minimal changes align with the request to add cache_strategy config to the base and provider configs, enable hook registration by Agent based on model config, and fixes in LiteLLM message formatting to support injection of cachePoint at the right level.

---

Patch follows.

# modification 1
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
<patched>19 class Model(abc.ABC):
20     """Abstract base class for Agent model providers.
21 
22     This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
23     standardized way to configure and process requests for different AI model providers.
24 
25     Attributes:
26         cache_strategy (Optional[str]): Strategy to use for prompt caching, e.g., "auto" for automatic caching.
27             This is propagated to all model implementations.
28     """
29 
30     cache_strategy: str | None = None
31 
32     @abc.abstractmethod
33     # pragma: no cover
34     def update_config(self, **model_config: Any) -> None:
35         """Update the model configuration with the provided arguments.
36 
37         Args:
38             **model_config: Configuration overrides.
39         """
40         pass
41 
42     @abc.abstractmethod
43     # pragma: no cover
44     def get_config(self) -> Any:
45         """Return the model configuration.
46 
47         Returns:
48             The model's configuration.
49         """
50         pass
51 
52     @abc.abstractmethod
53     # pragma: no cover
54     def structured_output(
55         self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
56     ) -> AsyncGenerator[dict[str, T | Any], None]:
57         """Get structured output from the model.
58 
59         Args:
60             output_model: The output model to use for the agent.
61             prompt: The prompt messages to use for the agent.
62             system_prompt: System prompt to provide context to the model.
63             **kwargs: Additional keyword arguments for future extensibility.
64 
65         Yields:
66             Model events with the last being the structured output.
67 
68         Raises:
69             ValidationException: The response format from the model does not match the output_model
70         """
71         pass
72 
73     @abc.abstractmethod
74     # pragma: no cover
75     def stream(
76         self,
77         messages: Messages,
78         tool_specs: list[ToolSpec] | None = None,
79         system_prompt: str | None = None,
80         *,
81         tool_choice: ToolChoice | None = None,
82         system_prompt_content: list[SystemContentBlock] | None = None,
83         invocation_state: dict[str, Any] | None = None,
84         **kwargs: Any,
85     ) -> AsyncIterable[StreamEvent]:
86         """Stream conversation with the model.
87 
88         This method handles the full lifecycle of conversing with the model:
89 
90         1. Format the messages, tool specs, and configuration into a streaming request
91         2. Send the request to the model
92         3. Yield the formatted message chunks
93 
94         Args:
95             messages: List of message objects to be processed by the model.
96             tool_specs: List of tool specifications to make available to the model.
97             system_prompt: System prompt to provide context to the model.
98             tool_choice: Selection strategy for tool invocation.
99             system_prompt_content: System prompt content blocks for advanced features like caching.
100             invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
101             **kwargs: Additional keyword arguments for future extensibility.
102 
103         Yields:
104             Formatted message chunks from the model.
105 
106         Raises:
107             ModelThrottledException: When the model service is throttling requests from the client.
108         """
109         pass
</patched>
</file>
```

# modification 2
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
188         # Automatically add ConversationCachingHook if model has cache_strategy="auto"
189         if getattr(self.model, "get_config", None):
190             config = self.model.get_config()
191             if config is not None and config.get("cache_strategy") == "auto":
192                 from strands.agent.conversation_caching_hook import ConversationCachingHook
193                 self.hooks.add_hook(ConversationCachingHook())
</patched>
</file>
```

# modification 3
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
78             cache_strategy: Optional cache strategy flag (e.g., "auto") for automatic prompt caching
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
121 </patched>
</file>
```

# modification 4
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
192         return self.config
</original>
<patched>176     def update_config(self, **model_config: Unpack[BedrockConfig]) -> None:  # type: ignore
177         """Update the Bedrock Model configuration with the provided arguments.
178 
179         Args:
180             **model_config: Configuration overrides.
181         """
182         validate_config_keys(model_config, self.BedrockConfig)
183         self.config.update(model_config)
184         # Propagate