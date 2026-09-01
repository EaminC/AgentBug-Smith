Reasoning:
The issue requests adding an `estimate_tokens` method to the `Model` interface for proactive token usage estimation prior to sending requests. This method should be implemented in each model provider using their respective native token counting APIs.

- In `Model` abstract base class (model.py), add the abstract method `estimate_tokens` with the signature and docstring described.
- In `AnthropicModel`, implement `estimate_tokens` by leveraging `anthropic.count_tokens` (from the Anthropic SDK). Use `format_request_messages` or similar logic to prepare messages in the expected form, then use `self.client.count_tokens` (or `anthropic.count_tokens`) to get the count.
- In `OpenAIModel`, implement `estimate_tokens` by formatting the messages into OpenAI compatible messages and then using the `tiktoken` library tokenizer appropriate for the model to count tokens.
- In `GeminiModel`, implement `estimate_tokens` by formatting the request into Gemini API compatible request format and then summing the tokens from each content part using Gemini client method `client.count_tokens` or the SDK token counting helper.
- In `LiteLLMModel`, implement `estimate_tokens` via `litellm.token_counter` utility that can count tokens for the formatted request.

For imports:
- Import necessary token counting helpers: `anthropic.count_tokens`, `tiktoken` for OpenAI, `litellm.token_counter`, and for Gemini utilize `genai.Client.count_tokens()` or similar.

Because we only have the partial context, we'll assume token counting utilities are available as noted in the issue description and implement accordingly.

---

# modification 1
```
<file>src/strands/models/model.py</file>
<original>49 class Model(abc.ABC):
50     """Abstract base class for Agent model providers.
51 
52     This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
53     standardized way to configure and process requests for different AI model providers.
54     """
55 
56     @property
57     def stateful(self) -> bool:
58         """Whether the model manages conversation state server-side.
59 
60         Returns:
61             False by default. Model providers that support server-side state should override this.
62         """
63         return False
64 
65     @property
66     def context_window_limit(self) -> int | None:
67         """Maximum context window size in tokens, or None if not configured."""
68         config = self.get_config()
69         return (
70             config.get("context_window_limit")
71             if isinstance(config, dict)
72             else getattr(config, "context_window_limit", None)
73         )
74 
75     @abc.abstractmethod
76     # pragma: no cover
77     def update_config(self, **model_config: Any) -> None:
78         """Update the model configuration with the provided arguments.
79 
80         Args:
81             **model_config: Configuration overrides.
82         """
83         pass
84 
85     @abc.abstractmethod
86     # pragma: no cover
87     def get_config(self) -> Any:
88         """Return the model configuration.
89 
90         Returns:
91             The model's configuration.
92         """
93         pass
94 
95     @abc.abstractmethod
96     # pragma: no cover
97     def structured_output(
98         self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
99     ) -> AsyncGenerator[dict[str, T | Any], None]:
100         """Get structured output from the model.
101 
102         Args:
103             output_model: The output model to use for the agent.
104             prompt: The prompt messages to use for the agent.
105             system_prompt: System prompt to provide context to the model.
106             **kwargs: Additional keyword arguments for future extensibility.
107 
108         Yields:
109             Model events with the last being the structured output.
110 
111         Raises:
112             ValidationException: The response format from the model does not match the output_model
113         """
114         pass
115 
116     @abc.abstractmethod
117     # pragma: no cover
118     def stream(
119         self,
120         messages: Messages,
121         tool_specs: list[ToolSpec] | None = None,
122         system_prompt: str | None = None,
123         *,
124         tool_choice: ToolChoice | None = None,
125         system_prompt_content: list[SystemContentBlock] | None = None,
126         invocation_state: dict[str, Any] | None = None,
127         **kwargs: Any,
128     ) -> AsyncIterable[StreamEvent]:
129         """Stream conversation with the model.
130 
131         This method handles the full lifecycle of conversing with the model:
132 
133         1. Format the messages, tool specs, and configuration into a streaming request
134         2. Send the request to the model
135         3. Yield the formatted message chunks
136 
137         Args:
138             messages: List of message objects to be processed by the model.
139             tool_specs: List of tool specifications to make available to the model.
140             system_prompt: System prompt to provide context to the model.
141             tool_choice: Selection strategy for tool invocation.
142             system_prompt_content: System prompt content blocks for advanced features like caching.
143             invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
144             **kwargs: Additional keyword arguments for future extensibility.
145 
146         Yields:
147             Formatted message chunks from the model.
148 
149         Raises:
150             ModelThrottledException: When the model service is throttling requests from the client.
151         """
152         pass
</original>
<patched>49 class Model(abc.ABC):
50     """Abstract base class for Agent model providers.
51 
52     This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
53     standardized way to configure and process requests for different AI model providers.
54     """
55 
56     @property
57     def stateful(self) -> bool:
58         """Whether the model manages conversation state server-side.
59 
60         Returns:
61             False by default. Model providers that support server-side state should override this.
62         """
63         return False
64 
65     @property
66     def context_window_limit(self) -> int | None:
67         """Maximum context window size in tokens, or None if not configured."""
68         config = self.get_config()
69         return (
70             config.get("context_window_limit")
71             if isinstance(config, dict)
72             else getattr(config, "context_window_limit", None)
73         )
74 
75     @abc.abstractmethod
76     # pragma: no cover
77     def update_config(self, **model_config: Any) -> None:
78         """Update the model configuration with the provided arguments.
79 
80         Args:
81             **model_config: Configuration overrides.
82         """
83         pass
84 
85     @abc.abstractmethod
86     # pragma: no cover
87     def get_config(self) -> Any:
88         """Return the model configuration.
89 
90         Returns:
91             The model's configuration.
92         """
93         pass
94 
95     @abc.abstractmethod
96     # pragma: no cover
97     def structured_output(
98         self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
99     ) -> AsyncGenerator[dict[str, T | Any], None]:
100         """Get structured output from the model.
101 
102         Args:
103             output_model: The output model to use for the agent.
104             prompt: The prompt messages to use for the agent.
105             system_prompt: System prompt to provide context to the model.
106             **kwargs: Additional keyword arguments for future extensibility.
107 
108         Yields:
109             Model events with the last being the structured output.
110 
111         Raises:
112             ValidationException: The response format from the model does not match the output_model
113         """
114         pass
115 
116     @abc.abstractmethod
117     # pragma: no cover
118     def stream(
119         self,
120         messages: Messages,
121         tool_specs: list[ToolSpec] | None = None,
122         system_prompt: str | None = None,
123         *,
124         tool_choice: ToolChoice | None = None,
125         system_prompt_content: list[SystemContentBlock] | None = None,
126         invocation_state: dict[str, Any] | None = None,
127         **kwargs: Any,
128     ) -> AsyncIterable[StreamEvent]:
129         """Stream conversation with the model.
130 
131         This method handles the full lifecycle of conversing with the model:
132 
133         1. Format the messages, tool specs, and configuration into a streaming request
134         2. Send the request to the model
135         3. Yield the formatted message chunks
136 
137         Args:
138             messages: List of message objects to be processed by the model.
139             tool_specs: List of tool specifications to make available to the model.
140             system_prompt: System prompt to provide context to the model.
141             tool_choice: Selection strategy for tool invocation.
142             system_prompt_content: System prompt content blocks for advanced features like caching.
143             invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
144             **kwargs: Additional keyword arguments for future extensibility.
145 
146         Yields:
147             Formatted message chunks from the model.
148 
149         Raises:
150             ModelThrottledException: When the model service is throttling requests from the client.
151         """
152         pass
153 
154     @abc.abstractmethod
155     # pragma: no cover
156     def estimate_tokens(
157         self,
158         messages: Messages,
159         tool_specs: list[ToolSpec] | None = None,
160         system_prompt: str | None = None,
161     ) -> int:
162         """Estimate token count for the given input before sending to model."""
163         pass
</patched>
</file>
```

# modification 2
```
<file>src/strands/models/anthropic.py</file>
<original>31 class AnthropicModel(Model):
32     """Anthropic model provider implementation."""
33 
34     EVENT_TYPES = {
35         "message_start",
36         "content_block_start",
37         "content_block_delta",
38         "content_block_stop",
39         "message_stop",
40     }
41 
42     OVERFLOW_MESSAGES = {
43         "prompt is too long:",
44         "input is too long",
45         "input length exceeds context window",
46         "input and output tokens exceed your context limit",
47     }
48 
49     class AnthropicConfig(BaseModelConfig, total=False):
50         """Configuration options for Anthropic models.
51 
52         Attributes:
53             max_tokens: Maximum number of tokens to generate.
54             model_id: Calude model ID (e.g., "claude-3-7-sonnet-latest").
55                 For a complete list of supported models, see
56                 https://docs.anthropic.com/en/docs/about-claude/models/all-models.
57             params: Additional model parameters (e.g., temperature).
58                 For a complete list of supported parameters, see https://docs.anthropic.com/en/api/messages.
59         """
60 
61         max_tokens: Required[int]
62         model_id: Required[str]
63         params: dict[str, Any] | None
64 
65     def __init__(self, *, client_args: dict[str, Any] | None = None, **model_config: Unpack[AnthropicConfig]):
66         """Initialize provider instance.
67 
68         Args:
69             client_args: Arguments for the underlying Anthropic client (e.g., api_key).
70                 For a complete list of supported arguments, see https://docs.anthropic.com/en/api/client-sdks.
71             **model_config: Configuration options for the Anthropic model.
72         """
73         validate_config_keys(model_config, self.AnthropicConfig)
74         self.config = AnthropicModel.AnthropicConfig(**model_config)
75 
76         logger.debug("config=<%s> | initializing", self.config)
77 
78         client_args = client_args or {}
79         self.client = anthropic.AsyncAnthropic(**client_args)
80 
81     @override
82     def update_config(self, **model_config: Unpack[AnthropicConfig]) -> None:  # type: ignore[override]
83         """Update the Anthropic model configuration with the provided arguments.
84 
85         Args:
86             **model_config: Configuration overrides.
87         """
88         validate_config_keys(model_config, self.AnthropicConfig)
89         self.config.update(model_config)
90 
91     @override
92     def get_config(self) -> AnthropicConfig:
93         """Get the Anthropic model configuration.
94 
95         Returns:
96             The Anthropic model configuration.
97         """
98         return self.config
</original>
<patched>31 class AnthropicModel(Model):
32     """Anthropic model provider implementation."""
33 
34     EVENT_TYPES = {
35         "message_start",
36         "content_block_start",
37         "content_block_delta",
38         "content_block_stop",
39         "message_stop",
40     }
41 
42     OVERFLOW_MESSAGES = {
43         "prompt is too long:",
44         "input is too long",
45         "input length exceeds context window",
46         "input and output tokens exceed your context limit",
47     }
48 
49     class AnthropicConfig(BaseModelConfig, total=False):
50         """Configuration options for Anthropic models.
51 
52         Attributes:
53             max_tokens: Maximum number of tokens to generate.
54             model_id: Calude model ID (e.g., "claude-3-7-sonnet-latest").
55                 For a complete list of supported models, see
56                 https://docs.anthropic.com/en/docs/about-claude/models/all-models.
57             params: Additional model parameters (e.g., temperature).
58                 For a complete list of supported parameters, see https://docs.anthropic.com/en/api/messages.
59         """
60 
61         max_tokens: Required[int]
62         model_id: Required[str]
63         params: dict[str, Any] | None
64 
65     def __init__(self, *, client_args: dict[str, Any] | None = None, **model_config: Unpack[AnthropicConfig]):
66         """Initialize provider instance.
67 
68         Args:
69             client_args: Arguments for the underlying Anthropic client (e.g., api_key).
70                 For a complete list of supported arguments, see https://docs.anthropic.com/en/api/client-sdks.
71             **model_config: Configuration options for the Anthropic model.
72         """
73         import anthropic
74         validate_config_keys(model_config, self.AnthropicConfig)
75         self.config = AnthropicModel.AnthropicConfig(**model_config)
76 
77         logger.debug("config=<%s> | initializing", self.config)
78 
79         client_args = client_args or {}
80         self.client = anthropic.AsyncAnthropic(**client_args)
81 
82     @override
83     def update_config(self, **model_config: Unpack[AnthropicConfig]) -> None:  # type: ignore[override]
84         """Update the Anthropic model configuration with the provided arguments.
85 
86         Args:
87             **model_config: Configuration overrides.
88         """
89         validate_config_keys(model_config, self.AnthropicConfig)
90         self.config.update(model_config)
91 
92     @override
93     def get_config(self) -> AnthropicConfig:
94         """Get the Anthropic model configuration.
95 
96         Returns:
97             The Anthropic model configuration.
98         """
99         return self.config
100 
101     @override
102     def estimate_tokens(
103         self, messages: Messages, tool_specs: list[ToolSpec] | None = None, system_prompt: str | None = None
104     ) -> int:
105         """Estimate token count for Anthropic formatted input using anthropic.count_tokens."""
106         import anthropic
107 
108         # Prepare messages in format suitable for counting
109         formatted_messages = self._format_request_messages(messages)
110         if system_prompt:
111             # Optionally prepend system prompt as a message
112             formatted_messages.insert(
113                 0, {"role": "system", "content": [{"text": system_prompt, "type": "text"}]}
114             )
115 
116         # Flatten message contents into strings for counting (Anthropic count_tokens expects strings)
117         message_texts = []
118         for m in formatted_messages:
119             content = m.get("content", [])
120             for block in content:
121                 if "text" in block:
122                     message_texts.append(block["text"])
123                 elif "thinking" in block:
124                     message_texts.append(block["thinking"])
125                 elif "source" in block:
126                     # For documents, images etc, we can count base64 string length as tokens approx
127                     # But safer to count empty or ignore them as they don't really count as tokens for prompt
128                     # We'll skip as unsupported for token count
129                     pass
130                 else:
131                     # fallback, try str
132                     message_texts.append(str(block))
133 
134         # Join all texts with newline separator for counting
135         joined_text = "\n".join(message_texts)
136 
137         # Use anthropic.count_tokens for the model
138         count = anthropic.count_tokens(joined_text)
139         return count
</patched>
</file>
```

# modification 3
```
<file>src/strands/models/openai.py</file>
<original>51 class OpenAIModel(Model):
52     """OpenAI model provider implementation."""
53 
54     client: Client
55 
56     class OpenAIConfig(BaseModelConfig, total=False):
57         """Configuration options for OpenAI models.
58 
59         Attributes:
60             model_id: Model ID (e.g., "gpt-4o").
61                 For a complete list of supported models, see https://platform.openai.com/docs/models.
62             params: Model parameters (e.g., max_tokens).
63                 For a complete list of supported parameters, see
64                 https://platform.openai.com/docs/api-reference/chat/create.
65         """
66 
67         model_id: str
68         params: dict[str, Any] | None
69 
70     def __init__(
71         self,
72         client: Client | None = None,
73         client_args: dict[str, Any] | None = None,
74         **model_config: Unpack[OpenAIConfig],
75     ) -> None:
76         """Initialize provider instance.
77 
78         Args:
79             client: Pre-configured OpenAI-compatible client to reuse across requests.
80                 When provided, this client will be reused for all requests and will NOT be closed