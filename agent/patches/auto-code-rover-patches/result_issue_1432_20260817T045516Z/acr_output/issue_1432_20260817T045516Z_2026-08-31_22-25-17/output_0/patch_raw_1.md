Reasoning:

To add support for `cache_strategy="auto"` for automatic prompt caching, the following changes are necessary:

1. In the base `Model` class (`model.py`), add a `cache_strategy` configuration attribute so all model providers support this config uniformly.

2. In the `Agent` class (`agent.py`), after initializing the model, if the model config's `cache_strategy` is `"auto"`, automatically add the `ConversationCachingHook` to `self.hooks`. This enables automatic cache point insertion.

3. In each model provider (BedrockModel, AnthropicModel, LiteLLMModel):

   - Extend their config schemas to include the optional `cache_strategy` argument by merging or extending the existing config dicts or TypedDicts.

   - Ensure the config is returned via `get_config()` including `cache_strategy`.

   - For BedrockModel, maintain the existing pass-through logic for handling cache points.

   - For AnthropicModel, convert injected `cachePoint` blocks into `cache_control` entries in the Anthropic request, consistent with existing logic.

   - For LiteLLMModel, fix the system prompt formatting so that injected `cachePoint` blocks with `"default"` type add proper `cache_control` message-level entries, respecting `cache_strategy="auto"`. This corrects their existing message-level handling.

These minimal changes will uniformly enable `cache_strategy="auto"` for prompt caching across all providers and auto-register the caching hook in the agent.

-----

Patch:

# modification 1: Add `cache_strategy` to Model base class as an optional config parameter

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
24     """
25 
25.1     def __init__(self, *, cache_strategy: str | None = None, **kwargs: Any) -> None:
25.2         # Store cache_strategy config at base class level to be inherited and accessible
25.3         self._cache_strategy = cache_strategy
25.4         if kwargs:
25.5             # Optionally handle additional config in derived classes
25.6             pass
25.7 
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
40.1         # Base config should expose cache_strategy if set
40.2         if hasattr(self, "_cache_strategy"):
40.3             base_config = {"cache_strategy": self._cache_strategy}
40.4         else:
40.5             base_config = {}
40.6 
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
</patched>
</file>
```

# modification 2: Add automatic hook registration for ConversationCachingHook in Agent if model config cache_strategy == "auto"

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
187 
188         # If not provided, create a new PrintingCallbackHandler instance
189         # If explicitly set to None, use null_callback_handler
190         # Otherwise use the passed callback_handler
191         self.callback_handler: Callable[..., Any] | PrintingCallbackHandler
192         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
193             self.callback_handler = PrintingCallbackHandler()
194         elif callback_handler is None:
195             self.callback_handler = null_callback_handler
196         else:
197             self.callback_handler = callback_handler
198 
199         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
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
188         # If not provided, create a new PrintingCallbackHandler instance
189         # If explicitly set to None, use null_callback_handler
190         # Otherwise use the passed callback_handler
191         self.callback_handler: Callable[..., Any] | PrintingCallbackHandler
192         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
193             self.callback_handler = PrintingCallbackHandler()
194         elif callback_handler is None:
195             self.callback_handler = null_callback_handler
196         else:
197             self.callback_handler = callback_handler
198 
198.1         # If the model cache_strategy is "auto", add ConversationCachingHook automatically
198.2         try:
198.3             cache_strategy = None
198.4             model_config = None
198.5             if hasattr(self.model, "get_config") and callable(getattr(self.model, "get_config")):
198.6                 model_config = self.model.get_config()
198.7 
198.8             if model_config and isinstance(model_config, dict):
198.9                 cache_strategy = model_config.get("cache_strategy")
199.0 
199.1             # Import ConversationCachingHook here to avoid circular import if needed
199.2             if cache_strategy == "auto":
199.3                 from strands.agent.hooks.conversation_caching import ConversationCachingHook
199.4                 self.hooks.add_hook(ConversationCachingHook())
199.5         except Exception:
199.6             # Fail silently or log error if import or attribute access fails
199.7             pass
199 
199         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
</patched>
</file>
```

# modification 3: Extend BedrockModel's config to include cache_strategy and ensure get_config returns it

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
</original>
<patched>69     class BedrockConfig(TypedDict, total=False):
70         """Configuration options for Bedrock models.
71 
72         Attributes:
73             additional_args: Any additional arguments to include in the request
74             additional_request_fields: Additional fields to include in the Bedrock request
75             additional_response_field_paths: Additional response field paths to extract
76             cache_prompt: Cache point type for the system prompt
77             cache_tools: Cache point type for tools
77.1           cache_strategy: Cache strategy string (e.g., "auto") to enable automatic prompt caching
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
102.1      cache_strategy: str | None
103         guardrail_id: str | None
104         guardrail_trace: Literal["enabled", "disabled", "enabled_full"] | None
105         guardrail_stream_processing_mode: Literal["sync", "async"] | None
106         guardrail_version: str | None
107         guardrail_redact_input: bool | None
108         guardrail_redact_input_message: str | None
109         guardrail_redact_output: bool | None
110         guardrail_redact_output_message: str | None