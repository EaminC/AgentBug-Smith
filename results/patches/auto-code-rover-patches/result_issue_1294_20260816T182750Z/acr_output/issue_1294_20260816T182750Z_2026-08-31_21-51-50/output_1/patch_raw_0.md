Reasoning:

The core request is to add an `estimate_tokens()` method to the Model interface and implement it for the different model classes (AnthropicModel, OpenAIModel, GeminiModel, LiteLLMModel) using their native token counting capabilities or libraries.

1. In `Model` (abstract base class), add the abstract method declaration for `estimate_tokens()` as described.
2. In AnthropicModel, implement the estimate_tokens method using `anthropic.count_tokens()`. For that, we'll first format the messages using `_format_request_messages`, then count tokens with `anthropic.count_tokens` passing the formatted messages. For tool_specs and system_prompt, we follow their usage in `format_request`.
3. In OpenAIModel, implement using the `tiktoken` library. We'll need to import `tiktoken` and use the tokenizer according to the model id. We convert messages formatted by `format_request_messages()` to OpenAI API chat message formats, then sum token counts per message accordingly.
4. In GeminiModel, implement `estimate_tokens` by formatting the request content and then using `model.count_tokens()` on it (Gemini's native counting method).
5. In LiteLLMModel, implement `estimate_tokens` by formatting the request with our existing `format_request` and then calling a LiteLLM token counting function, `litellm.token_counter()`, on that formatted request.

Additional notes:
- For OpenAI token estimation, this requires importing tiktoken library which must be imported.
- For Anthropic, we assume `anthropic.count_tokens()` is available.
- For LiteLLM, `litellm.token_counter()` is assumed present.
- For Gemini, we assume we can get a client and call `model.count_tokens()` on the content.

Now we prepare the patch accordingly.

---

Patch:

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
152         pass</original>
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
99 
100     def _format_request_message_content(self, content: ContentBlock) -> dict[str, Any]:
101         """Format an Anthropic content block.
102 
103         Args:
104             content: Message content.
105 
106         Returns:
107             Anthropic formatted content block.
108 
109         Raises:
110             TypeError: If the content block type cannot be converted to an Anthropic-compatible format.
111         """
112         if "document" in content:
113             mime_type = mimetypes.types_map.get(f".{content['document']['format']}", "application/octet-stream")
114             return {
115                 "source": {
116                     "data": (
117                         content["document"]["source"]["bytes"].decode("utf-8")
118                         if mime_type == "text/plain"
119                         else base64.b64encode(content["document"]["source"]["bytes"]).decode("utf-8")
120                     ),
121                     "media_type": mime_type,
122                     "type": "text" if mime_type == "text/plain" else "base64",
123                 },
124                 "title": content["document"]["name"],
125                 "type": "document",
126             }
127 
128         if "image" in content:
129             return {
130                 "source": {
131                     "data": base64.b64encode(content["image"]["source"]["bytes"]).decode("utf-8"),
132                     "media_type": mimetypes.types_map.get(f".{content['image']['format']}", "application/octet-stream"),
133                     "type": "base64",
134                 },
135                 "type": "image",
136             }
137 
138         if "reasoningContent" in content:
139             return {
140                 "signature": content["reasoningContent"]["reasoningText"]["signature"],
141                 "thinking": content["reasoningContent"]["reasoningText"]["text"],
142                 "type": "thinking",
143             }
144 
145         if "text" in content:
146             return {"text": content["text"], "type": "text"}
147 
148         if "toolUse" in content:
149             return {
150                 "id": content["toolUse"]["toolUseId"],
151                 "input": content["toolUse"]["input"],
152                 "name": content["toolUse"]["name"],
153                 "type": "tool_use",
154             }
155 
156         if "toolResult" in content:
157             return {
158                 "content": [
159                     self._format_request_message_content(
160                         {"text": json.dumps(tool_result_content["json"])}
161                         if "json" in tool_result_content
162                         else cast(ContentBlock, tool_result_content)
163                     )
164                     for tool_result_content in content["toolResult"]["content"]
165                 ],
166                 "is_error": content["toolResult"]["status"] == "error",
167                 "tool_use_id": content["toolResult"]["toolUseId"],
168                 "type": "tool_result",
169             }
170 
171         raise TypeError(f"content_type=<{next(iter(content))}> | unsupported type")
172 
173     def _format_request_messages(self, messages: Messages) -> list[dict[str, Any]]:
174         """Format an Anthropic messages array.
175 
176         Args:
177             messages: List of message objects to be processed by the model.
178 
179         Returns:
180             An Anthropic messages array.
181         """
182         formatted_messages = []
183 
184         for message in messages:
185             formatted_contents: list[dict[str, Any]] = []
186 
187             for content in message["content"]:
188                 if "cachePoint" in content:
189                     formatted_contents[-1]["cache_control"] = {"type": "ephemeral"}
190                     continue
191 
192                 # Check for location sources in image, document, or video content
193                 if _has_location_source(content):
194                     logger.warning("Location sources are not supported by Anthropic | skipping content block")
195                     continue
196 
197                 formatted_contents.append(self._format_request_message_content(content))
198 
199             if formatted_contents:
200                 formatted_messages.append({"content": formatted_contents, "role": message["role"]})
201 
202         return formatted_messages
203 
204     def format_request(
205         self,
206         messages: Messages,
207         tool_specs: list[ToolSpec] | None = None,
208         system_prompt: str | None = None,
209         tool_choice: ToolChoice | None = None,
210     ) -> dict[str, Any]:
211         """Format an Anthropic streaming request.
212 
213         Args:
214             messages: List of message objects to be processed by the model.
215             tool_specs: List of tool specifications to make available to the model.
216             system_prompt: System prompt to provide context to the model.
217             tool_choice: Selection strategy for tool invocation.
218 
219         Returns:
220             An Anthropic streaming request.
221 
222         Raises:
223             TypeError: If a message contains a content block type that cannot be converted to an Anthropic-compatible
224                 format.
225         """
226         return {
227             "max_tokens": self.config["max_tokens"],
228             "messages": self._format_request_messages(messages),
229             "model": self.config["model_id"],
230             "tools": [
231                 {
232                     "name": tool_spec["name"],
233                     "description": tool_spec["description"],
234                     "input_schema": tool_spec["inputSchema"]["json"],
235                 }
236                 for tool_spec in tool_specs or []
237             ],
238             **(self._format_tool_choice(tool_choice)),
239             **({"system": system_prompt} if system_prompt else {}),
240             **(self.config.get("params") or {}),
241         }
241 
242     @staticmethod
243     def _format_tool_choice(tool_choice: ToolChoice | None) -> dict:
244         if tool_choice is None:
245             return {}
246 
