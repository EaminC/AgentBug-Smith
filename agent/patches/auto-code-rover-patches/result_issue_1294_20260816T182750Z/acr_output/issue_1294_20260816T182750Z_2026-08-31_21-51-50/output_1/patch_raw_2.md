Reasoning:

The issue requests adding a method estimate_tokens() to the Model abstract base class to enable token count estimation before making API calls, to aid proactive context management. Thus, first, we must add an abstract estimate_tokens method to Model.

Then, in the model provider implementations (AnthropicModel, OpenAIModel, GeminiModel, LiteLLMModel), implement estimate_tokens() method leveraging their provider-specific token counting APIs or libraries.

- AnthropicModel: Use `anthropic.count_tokens()` applied to the formatted messages as Anthropic expects.

- OpenAIModel: Use tiktoken's tokenizer to count tokens for the formatted messages + system prompt.

- GeminiModel: Use the client's/native method model.count_tokens() on the formatted request content.

- LiteLLMModel: Use `litellm.token_counter()` on the formatted messages structure.

No other modifications are needed for now.

Note:

- Need to import relevant token counting utilities in the respective modules (tiktoken in openai.py, anthropic in anthropic.py, litellm in litellm.py).

- In OpenAIModel, instantiate the appropriate tokenizer and count tokens for the formatted messages.

- Ensure that the estimate_tokens method signature matches the interface.

Now, provide the patch as requested.

---

# modification 1: Add abstract estimate_tokens to Model base class

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
```

---

# modification 2: Implement estimate_tokens in AnthropicModel using anthropic.count_tokens

```
<file>src/strands/models/anthropic.py</file>
<original>30 class AnthropicModel(Model):
31     """Anthropic model provider implementation."""
32 
33     EVENT_TYPES = {
34         "message_start",
35         "content_block_start",
36         "content_block_delta",
37         "content_block_stop",
38         "message_stop",
39     }
40 
41     OVERFLOW_MESSAGES = {
42         "prompt is too long:",
43         "input is too long",
44         "input length exceeds context window",
45         "input and output tokens exceed your context limit",
46     }
47 
48     class AnthropicConfig(BaseModelConfig, total=False):
49         """Configuration options for Anthropic models.
50 
51         Attributes:
52             max_tokens: Maximum number of tokens to generate.
53             model_id: Calude model ID (e.g., "claude-3-7-sonnet-latest").
54                 For a complete list of supported models, see
55                 https://docs.anthropic.com/en/docs/about-claude/models/all-models.
56             params: Additional model parameters (e.g., temperature).
57                 For a complete list of supported parameters, see https://docs.anthropic.com/en/api/messages.
58         """
59 
60         max_tokens: Required[int]
61         model_id: Required[str]
62         params: dict[str, Any] | None
63 
64     def __init__(self, *, client_args: dict[str, Any] | None = None, **model_config: Unpack[AnthropicConfig]):
65         """Initialize provider instance.
66 
67         Args:
68             client_args: Arguments for the underlying Anthropic client (e.g., api_key).
69                 For a complete list of supported arguments, see https://docs.anthropic.com/en/api/client-sdks.
70             **model_config: Configuration options for the Anthropic model.
71         """
72         validate_config_keys(model_config, self.AnthropicConfig)
73         self.config = AnthropicModel.AnthropicConfig(**model_config)
74 
75         logger.debug("config=<%s> | initializing", self.config)
76 
77         client_args = client_args or {}
78         self.client = anthropic.AsyncAnthropic(**client_args)
79 
80     @override
81     def update_config(self, **model_config: Unpack[AnthropicConfig]) -> None:  # type: ignore[override]
82         """Update the Anthropic model configuration with the provided arguments.
83 
84         Args:
85             **model_config: Configuration overrides.
86         """
87         validate_config_keys(model_config, self.AnthropicConfig)
88         self.config.update(model_config)
89 
90     @override
91     def get_config(self) -> AnthropicConfig:
92         """Get the Anthropic model configuration.
93 
94         Returns:
95             The Anthropic model configuration.
96         """
97         return self.config
98 
99     def _format_request_message_content(self, content: ContentBlock) -> dict[str, Any]:
100         """Format an Anthropic content block.
101 
102         Args:
103             content: Message content.
104 
105         Returns:
106             Anthropic formatted content block.
107 
108         Raises:
109             TypeError: If the content block type cannot be converted to an Anthropic-compatible format.
110         """
111         if "document" in content:
112             mime_type = mimetypes.types_map.get(f".{content['document']['format']}", "application/octet-stream")
113             return {
114                 "source": {
115                     "data": (
116                         content["document"]["source"]["bytes"].decode("utf-8")
117                         if mime_type == "text/plain"
118                         else base64.b64encode(content["document"]["source"]["bytes"]).decode("utf-8")
119                     ),
120                     "media_type": mime_type,
121                     "type": "text" if mime_type == "text/plain" else "base64",
122                 },
123                 "title": content["document"]["name"],
124                 "type": "document",
125             }
126 
127         if "image" in content:
128             return {
129                 "source": {
130                     "data": base64.b64encode(content["image"]["source"]["bytes"]).decode("utf-8"),
131                     "media_type": mimetypes.types_map.get(f".{content['image']['format']}", "application/octet-stream"),
132                     "type": "base64",
133                 },
134                 "type": "image",
135             }
136 
137         if "reasoningContent" in content:
138             return {
139                 "signature": content["reasoningContent"]["reasoningText"]["signature"],
140                 "thinking": content["reasoningContent"]["reasoningText"]["text"],
141                 "type": "thinking",
142             }
143 
144         if "text" in content:
145             return {"text": content["text"], "type": "text"}
146 
147         if "toolUse" in content:
148             return {
149                 "id": content["toolUse"]["toolUseId"],
150                 "input": content["toolUse"]["input"],
151                 "name": content["toolUse"]["name"],
152                 "type": "tool_use",
153             }
154 
155         if "toolResult" in content:
156             return {
157                 "content": [
158                     self._format_request_message_content(
159                         {"text": json.dumps(tool_result_content["json"])}
160                         if "json" in tool_result_content
161                         else cast(ContentBlock, tool_result_content)
162                     )
163                     for tool_result_content in content["toolResult"]["content"]
164                 ],
165                 "is_error": content["toolResult"]["status"] == "error",
166                 "tool_use_id": content["toolResult"]["toolUseId"],
167                 "type": "tool_result",
168             }
169 
170         raise TypeError(f"content_type=<{next(iter(content))}> | unsupported type")
171 
172     def _format_request_messages(self, messages: Messages) -> list[dict[str, Any]]:
173         """Format an Anthropic messages array.
174 
175         Args:
176             messages: List of message objects to be processed by the model.
177 
178         Returns:
179             An Anthropic messages array.
180         """
181         formatted_messages = []
182 
183         for message in messages:
184             formatted_contents: list[dict[str, Any]] = []
185 
186             for content in message["content"]:
187                 if "cachePoint" in content:
188                     formatted_contents[-1]["cache_control"] = {"type": "ephemeral"}
189                     continue
190 
191                 # Check for location sources in image, document, or video content
192                 if _has_location_source(content):
193                     logger.warning("Location sources are not supported by Anthropic | skipping content block")
194                     continue
195 
196                 formatted_contents.append(self._format_request_message_content(content))
197 
198             if formatted_contents:
199                 formatted_messages.append({"content": formatted_contents, "role": message["role"]})
200 
201         return formatted_messages
202 
203     def format_request(
204         self,
205         messages: Messages,
206         tool_specs: list[ToolSpec] | None = None,
207         system_prompt: str | None = None,
208         tool_choice: ToolChoice | None = None,
209     ) -> dict[str, Any]:
210         """Format an Anthropic streaming request.
211 
212         Args:
213             messages: List of message objects to be processed by the model.
214             tool_specs: List of tool specifications to make available to the model.
215             system_prompt: System prompt to provide context to the model.
216             tool_choice: Selection strategy for tool invocation.
217 
218         Returns:
219             An Anthropic streaming request.
220 
221         Raises:
222             TypeError: If a message contains a content block type that cannot be converted to an Anthropic-compatible
223                 format.
224         """
225         return {
226             "max_tokens": self.config["max_tokens"],
227             "messages": self._format_request_messages(messages),
228             "model": self.config["model_id"],
229             "tools": [
230                 {
231                     "name": tool_spec["name"],
232                     "description": tool_spec["description"],
233                     "input_schema": tool_spec["inputSchema"]["json"],
234                 }
235                 for tool_spec in tool_specs or []
236             ],
237             **(self._format_tool_choice(tool_choice)),
238             **({"system": system_prompt} if system_prompt else {}),
239             **(self.config.get("params") or {}),
240         }
241 
242     @staticmethod
243     def _format_tool_choice(tool_choice: ToolChoice | None) -> dict:
244         if tool_choice is None:
245             return {}
246 
247         if "any" in tool_choice:
248             return {"tool_choice": {"type": "any"}}
249         elif "auto" in tool_choice:
250             return {"tool_choice": {"type": "auto"}}
251         elif "tool" in tool_choice:
252             return {"tool_choice": {"type": "tool", "name": cast(ToolChoiceToolDict, tool_choice)["tool