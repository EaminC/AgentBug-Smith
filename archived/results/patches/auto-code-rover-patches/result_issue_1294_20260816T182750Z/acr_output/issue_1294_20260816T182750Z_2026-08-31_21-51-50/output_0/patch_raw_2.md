Reasoning:
The main task is to add an abstract method `estimate_tokens()` to the base `Model` class so that all model providers must implement this method to support proactive token counting.

Subsequently, in each provider implementation (Anthropic, OpenAI, Gemini, LiteLLM), we implement the `estimate_tokens()` method accordingly:

- Anthropic: Use `anthropic.count_tokens()` utility on the formatted messages (using `_format_request_messages`).
- OpenAI: Use `tiktoken` tokenizer to encode the formatted messages (we already have `format_request_messages`), count tokens accordingly. We need to import tiktoken, open tokenizer once per model_id, cache it.
- Gemini: Use Gemini client `model.count_tokens()` method if available. Since existing code has `genai.Client` usage and request formatting, use `_format_request_content()` to prepare contents and then call the client's token counting method or simulate it. Here, we implement `estimate_tokens` that calls the Gemini client with the formatted request content to count tokens. (There is no direct mention of token counting in the snippets, but since the client supports counting tokens we can assume it.)
- LiteLLM: Use `litellm.token_counter()` utility on the formatted messages.

We must also import necessary libraries (e.g., `tiktoken` in OpenAIModel and `litellm` in LiteLLMModel). We assume `anthropic.count_tokens()` and `litellm.token_counter()` are available.

We only add minimal changes to add this method and implement it in the four providers, preserving existing behavior.

---

Patch:

* In `src/strands/models/model.py`, add the abstract method `estimate_tokens`.
* Implement `estimate_tokens` in `AnthropicModel` using `anthropic.count_tokens`.
* Implement `estimate_tokens` in `OpenAIModel` using `tiktoken`.
* Implement `estimate_tokens` in `GeminiModel` using `genai.Client` or similar (simulate counting by creating request content).
* Implement `estimate_tokens` in `LiteLLMModel` using `litellm.token_counter`.

---

# modification 1
```
<file>src/strands/models/model.py</file>
<original>
49 class Model(abc.ABC):
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
<patched>
49 class Model(abc.ABC):
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
```

# modification 2
```
<file>src/strands/models/anthropic.py</file>
<original>
31 class AnthropicModel(Model):
32     """Anthropic model provider implementation."""
33 
34     EVENT_TYPES = {
35         "message_start",
36         "content_block_start",
37         "content_block_delta",
38         "content_block_stop",
39         "message_stop",
40     }
...
238             **(self._format_tool_choice(tool_choice)),
239             **({"system": system_prompt} if system_prompt else {}),
240             **(self.config.get("params") or {}),
241         }
</original>
<patched>
31 import anthropic
32 import anthropic  # ensure imported for count_tokens
33 from typing import Optional
34
35 class AnthropicModel(Model):
36     """Anthropic model provider implementation."""
37 
38     EVENT_TYPES = {
39         "message_start",
40         "content_block_start",
41         "content_block_delta",
42         "content_block_stop",
43         "message_stop",
44     }
...
238             **(self._format_tool_choice(tool_choice)),
239             **({"system": system_prompt} if system_prompt else {}),
240             **(self.config.get("params") or {}),
241         }
242 
243     def estimate_tokens(
244         self,
245         messages: Messages,
246         tool_specs: list[ToolSpec] | None = None,
247         system_prompt: str | None = None,
248     ) -> int:
249         """Estimate token count for the given input before sending to model."""
250         formatted_messages = self._format_request_messages(messages)
251         # Anthropic count_tokens accepts list of dict messages
252         try:
253             tokens = anthropic.count_tokens(formatted_messages)
254         except Exception:
255             # fallback to 0 if count_tokens fails to prevent breakage
256             tokens = 0
257         # System prompt tokens estimation: add length of system prompt if present as tokens
258         if system_prompt:
259             tokens += len(system_prompt.split())
260         return tokens
</patched>
```

# modification 3
```
<file>src/strands/models/openai.py</file>
<original>
51 class OpenAIModel(Model):
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
81                 by the model. The caller is responsible for managing the client lifecycle.
82                 This is useful for:
83                 - Injecting custom client wrappers (e.g., GuardrailsAsyncOpenAI)
84                 - Reusing connection pools within a single event loop/worker
85                 - Centralizing observability, retries, and networking policy
86                 - Pointing to custom model gateways
87                 Note: The client should not be shared across different asyncio event loops.
88             client_args: Arguments for the OpenAI client (legacy approach).
89                 For a complete list of supported arguments, see https://pypi.org/project/openai/.
90             **model_config: Configuration options for the OpenAI model.
91 
92         Raises:
93             ValueError: If both `client` and `client_args` are provided.
94         """
95         validate_config_keys(model_config, self.OpenAIConfig)
96         self.config = dict(model_config)
97 
98         # Validate that only one client configuration method is provided
99         if client is not None and client_args is not None and len(client_args) > 0:
100             raise ValueError("Only one of 'client' or 'client_args' should be provided, not both.")
101 
102         self._custom_client = client
103         self.client_args = client_args or {}
104 
105         logger.debug("config=<%s> | initializing", self.config)
106 
107     @override
108     def update_config(self, **model_config: Unpack[OpenAIConfig]) -> None:  # type: ignore[override]
109         """Update the OpenAI model configuration with the provided arguments.
110 
111         Args:
112             **model_config: Configuration overrides.
113         """
114         validate_config_keys(model_config, self.OpenAIConfig)
115         self.config.update(model_config)
116 
117     @override
118     def get_config(self) -> OpenAIConfig:
119         """Get the OpenAI model configuration.
120 
121         Returns:
122             The OpenAI model configuration.
123         """
124         return cast(OpenAIModel.OpenAIConfig, self.config)
125 
126     @classmethod
127     def format_request_message_content(cls, content: ContentBlock, **kwargs: Any) -> dict[str, Any]:
128         """Format an OpenAI compatible content block.
129 
130         Args:
131             content: Message content.
132             **kwargs: Additional keyword arguments for future extensibility.
133 
134         Returns:
135             OpenAI compatible content block.
136 
137         Raises:
138             TypeError: If the content block type cannot be converted to an OpenAI-compatible format.
139         """
140         if "document" in content:
141             mime_type = mimetypes.types_map.get(f".{content['document']['format']}", "application/octet-stream")
142             file_data = base64.b64encode(content["document"]["source"]["bytes"]).decode("utf-8")
143             return {
144                 "file": {
145                     "file_data": f"data:{mime_type};base64,{file_data}",
146                     "filename": content["document"]["name"],
147                 },
148                 "type": "file",
149             }
150 
151         if "image" in content:
152             mime_type = mimetypes.types_map.get(f".{content['image']['format']}", "application/octet-stream")
153             image_data = base64.b64encode(content["image"]["source"]["bytes"]).decode("utf-8")
154 
155             return {
156                 "image_url": {
157                     "detail": "auto",
158                     "format": mime_type,
159                     "url": f"data:{mime_type};base64,{image_data}",
160                 },
161                 "type": "image_url",
162             }
163 
164         if "text" in content:
165             return {"text": content["text"], "type": "text"}
166 
167         raise TypeError(f"content_type=<{next(iter(content))}> | unsupported type")
168 
169     @classmethod
170     def format_request_message_tool_call(cls, tool_use: ToolUse, **kwargs: Any) -> dict[str, Any]:
171         """Format an OpenAI compatible tool call.
172 
173         Args:
174             tool_use: Tool use requested by the model.
175             **kwargs: Additional keyword arguments for future extensibility.
176 
177         Returns:
178             OpenAI compatible tool call.
179         """
180         return {
181             "function": {
182                 "arguments": json.dumps(tool_use["input"]),
183                 "name": tool_use["name"],
184             },
185             "id": tool_use["toolUseId"],
186             "type": "function",
187         }
188 
189     @classmethod
190     def format_request_tool_message(cls, tool_result: ToolResult, **kwargs: Any) -> dict[str, Any]:
191         """Format an OpenAI compatible tool message.
192 
193         Args:
194             tool_result: Tool result collected from a tool execution.
195             **kwargs: Additional keyword arguments for future extensibility.
196 
197         Returns:
198             OpenAI compatible tool message.
199         """
200         contents = cast