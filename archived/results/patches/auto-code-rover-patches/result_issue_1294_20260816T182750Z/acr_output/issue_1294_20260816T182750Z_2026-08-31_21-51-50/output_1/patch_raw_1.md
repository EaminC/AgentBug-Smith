Reasoning:

The problem requires adding an `estimate_tokens` method to the abstract `Model` base class and implementing the method concretely for model providers where token counting can be done prior to sending the request. This is for proactive token usage management.

- The abstract base class `Model` should get a new abstract method `estimate_tokens()` matching the proposed signature.
- The `AnthropicModel` class should implement the method using `anthropic.count_tokens()` count on the formatted messages.
- The `OpenAIModel` class should implement using the `tiktoken` library based on the formatted messages.
- The `GeminiModel` class should implement using the Gemini client model's `count_tokens()` method on the formatted request content.
- The `LiteLLMModel` class should implement using `litellm.token_counter()` API on the formatted request messages.

Each provider should delegate formatting the request messages to existing formatting methods, and then leverage native SDK token counting if possible.

Patch:

```python
<file>src/strands/models/model.py</file>
<original>56     @property
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
<patched>56     @property
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

```python
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
...</original>
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
...
187     @override
188     def estimate_tokens(
189         self,
190         messages: Messages,
191         tool_specs: list[ToolSpec] | None = None,
192         system_prompt: str | None = None,
193     ) -> int:
194         """Estimate token count for the given input before sending to Anthropic model."""
195         # Use Anthropic's count_tokens function on formatted messages
196         try:
197             # Compose request dictionary similar to format_request but for counting tokens
198             request = self.format_request(messages, tool_specs, system_prompt)
199             # Anthropic SDK count_tokens expects messages in the Anthropic format
200             count = anthropic.count_tokens(request["messages"])
201             return count
202         except Exception as e:
203             logger.warning(f"Failed to estimate tokens for Anthropic model: {e}")
204             return 0
</patched>
</file>

```

```python
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
200         contents = cast(
201             list[ContentBlock],
202             [
203                 {"text": json.dumps(content["json"])} if "json" in content else content
204                 for content in tool_result["content"]
205             ],
206         )
207 
208         # Merge adjacent text blocks while preserving the order of non-text
209         # (image/document) content.  When all content is text, join into a
210         # single string for broad compatibility with OpenAI-compatible
211         # endpoints (e.g., Kimi K2.5, vLLM, Ollama).
212         # See https://github.com/strands-agents/sdk-python/issues/1696
213         merged: list[dict[str, Any]] = []
214         has_non_text = False
215         for content_block in contents:
216             if "text" in content_block:
217                 # Merge with the previous entry if it is also text (adjacent)
218                 if merged and merged[-1].get("type") == "text":
219                     merged[-1]["text"] += "\n" + content_block["text"]
220                 else:
221                     merged.append({"type": "text", "text": content_block["text"]})
222             elif "image" in content_block or "document" in content_block:
223                 has_non_text = True
224                 merged.append(cls.format_request_message_content(content_block))
225 
226         content: str | list[dict[str, Any]]
227         if has_non_text:
228             # Keep array format when images/documents are present so that
229             # _split_tool_message_images can extract them