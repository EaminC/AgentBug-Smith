Reasoning:
To implement the feature described, minimal required changes are:

1. Add a new optional attribute `cache_strategy: Optional[str] = None` to the base `Model` class so that all providers have that configuration option.

2. Modify the `Agent` constructor (`__init__` method) to detect if `cache_strategy == "auto"` on the model's config. 
   If so, register (add) an instance of `ConversationCachingHook` to the agent's hook registry.

This will enable the "auto" cache strategy as a standard config and automatically activate the caching hook in the agent, satisfying the design.

No other changes are strictly needed for these requirements, assuming `ConversationCachingHook` is already implemented and available to import.

---

Patch:

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
<patched>import typing
from typing import Optional

class Model(abc.ABC):
    """Abstract base class for Agent model providers.

    This class defines the interface for all model implementations in the Strands Agents SDK. It provides a
    standardized way to configure and process requests for different AI model providers.
    """

    cache_strategy: Optional[str] = None

    @abc.abstractmethod
    # pragma: no cover
    def update_config(self, **model_config: Any) -> None:
        """Update the model configuration with the provided arguments.

        Args:
            **model_config: Configuration overrides.
        """
        pass

    @abc.abstractmethod
    # pragma: no cover
    def get_config(self) -> Any:
        """Return the model configuration.

        Returns:
            The model's configuration.
        """
        pass

    @abc.abstractmethod
    # pragma: no cover
    def structured_output(
        self, output_model: type[T], prompt: Messages, system_prompt: str | None = None, **kwargs: Any
    ) -> AsyncGenerator[dict[str, T | Any], None]:
        """Get structured output from the model.

        Args:
            output_model: The output model to use for the agent.
            prompt: The prompt messages to use for the agent.
            system_prompt: System prompt to provide context to the model.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Model events with the last being the structured output.

        Raises:
            ValidationException: The response format from the model does not match the output_model
        """
        pass

    @abc.abstractmethod
    # pragma: no cover
    def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        """Stream conversation with the model.

        This method handles the full lifecycle of conversing with the model:

        1. Format the messages, tool specs, and configuration into a streaming request
        2. Send the request to the model
        3. Yield the formatted message chunks

        Args:
            messages: List of message objects to be processed by the model.
            tool_specs: List of tool specifications to make available to the model.
            system_prompt: System prompt to provide context to the model.
            tool_choice: Selection strategy for tool invocation.
            system_prompt_content: System prompt content blocks for advanced features like caching.
            invocation_state: Caller-provided state/context that was passed to the agent when it was invoked.
            **kwargs: Additional keyword arguments for future extensibility.

        Yields:
            Formatted message chunks from the model.

        Raises:
            ModelThrottledException: When the model service is throttling requests from the client.
        """
        pass
</patched>
</file>
```

# modification 2
```
<file>src/strands/agent/agent.py</file>
<original>102     def __init__(
103         self,
104         model: Model | str | None = None,
105         messages: Messages | None = None,
106         tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
107         system_prompt: str | list[SystemContentBlock] | None = None,
108         structured_output_model: type[BaseModel] | None = None,
109         callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
110         conversation_manager: ConversationManager | None = None,
111         record_direct_tool_call: bool = True,
112         load_tools_from_directory: bool = False,
113         trace_attributes: Mapping[str, AttributeValue] | None = None,
114         *,
115         agent_id: str | None = None,
116         name: str | None = None,
117         description: str | None = None,
118         state: AgentState | dict | None = None,
119         hooks: list[HookProvider] | None = None,
120         session_manager: SessionManager | None = None,
121         tool_executor: ToolExecutor | None = None,
122         retry_strategy: ModelRetryStrategy | None = None,
123     ):
124         """Initialize the Agent with the specified configuration.
125 
126         Args:
127             model: Provider for running inference or a string representing the model-id for Bedrock to use.
128                 Defaults to strands.models.BedrockModel if None.
129             messages: List of initial messages to pre-load into the conversation.
130                 Defaults to an empty list if None.
131             tools: List of tools to make available to the agent.
132                 Can be specified as:
133 
134                 - String tool names (e.g., "retrieve")
135                 - File paths (e.g., "/path/to/tool.py")
136                 - Imported Python modules (e.g., from strands_tools import current_time)
137                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
138                 - ToolProvider instances for managed tool collections
139                 - Functions decorated with `@strands.tool` decorator.
140 
141                 If provided, only these tools will be available. If None, all tools will be available.
142             system_prompt: System prompt to guide model behavior.
143                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
144                 If None, the model will behave according to its default settings.
145             structured_output_model: Pydantic model type(s) for structured output.
146                 When specified, all agent calls will attempt to return structured output of this type.
147                 This can be overridden on the agent invocation.
148                 Defaults to None (no structured output).
149             callback_handler: Callback for processing events as they happen during agent execution.
150                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
151                 If explicitly set to None, null_callback_handler is used.
152             conversation_manager: Manager for conversation history and context window.
153                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
154             record_direct_tool_call: Whether to record direct tool calls in message history.
155                 Defaults to True.
156             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
157                 Defaults to False.
158             trace_attributes: Custom trace attributes to apply to the agent's trace span.
159             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
160                 Defaults to "default".
161             name: name of the Agent
162                 Defaults to "Strands Agents".
163             description: description of what the Agent does
164                 Defaults to None.
165             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
166                 Defaults to an empty AgentState object.
167             hooks: hooks to be added to the agent hook registry
168                 Defaults to None.
169             session_manager: Manager for handling agent sessions including conversation history and state.
170                 If provided, enables session-based persistence and state management.
171             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
172             retry_strategy: Strategy for retrying model calls on throttling or other transient errors.
173                 Defaults to ModelRetryStrategy with max_attempts=6, initial_delay=4s, max_delay=240s.
174                 Implement a custom HookProvider for custom retry logic, or pass None to disable retries.
175 
176         Raises:
177             ValueError: If agent id contains path separators.
178         """
179         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
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
200 
201         # Process trace attributes to ensure they're of compatible types
202         self.trace_attributes: dict[str, AttributeValue] = {}
203         if trace_attributes:
204             for k, v in trace_attributes.items():
205                 if isinstance(v, (str, int, float, bool)) or (
206                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
207                 ):
208                     self.trace_attributes[k] = v
209 
210         self.record_direct_tool_call = record_direct_tool_call
211         self.load_tools_from_directory = load_tools_from_directory
212 
213         self.tool_registry = ToolRegistry()
214 
215         # Process tool list if provided
216         if tools is not None:
217             self.tool_registry.process_tools(tools)
218 
219         # Initialize tools and configuration
220         self.tool_registry.initialize_tools(self.load_tools_from_directory)
221         if load_tools_from_directory:
222             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
223 
224         self.event_loop_metrics = EventLoopMetrics()
225 
226         # Initialize tracer instance (no-op if not configured)
227         self.tracer = get_tracer()
228         self.trace_span: trace_api.Span | None = None
229 
230         # Initialize agent state management
231         if state is not None:
232             if isinstance(state, dict):
233                 self.state = AgentState(state)
234             elif isinstance(state, AgentState):
235                 self.state = state
236             else:
237                 raise ValueError("state must be an AgentState object or a dict")
238         else:
239             self.state = AgentState()
240 
241         self.tool_caller = _ToolCaller(self)
242 
243         self.hooks = HookRegistry()
244 
245         self._interrupt_state = _InterruptState()
246 
247         # Initialize lock for guarding concurrent invocations
248         # Using threading.Lock instead of asyncio.Lock because run_async() creates
249         # separate event loops in different threads, so asyncio.Lock wouldn't work
250         self._invocation_lock = threading.Lock()
251 
252         # In the future, we'll have a RetryStrategy base class but until
253         # that API is determined we only allow ModelRetryStrategy
254         if retry_strategy and type(retry_strategy) is not ModelRetryStrategy:
255             raise ValueError("retry_strategy must be an instance of ModelRetryStrategy")
256 
257         self._retry_strategy = (
258             retry_strategy
259             if retry_strategy is not None
260             else ModelRetryStrategy(max_attempts=MAX_ATTEMPTS, max_delay=MAX_DELAY, initial_delay=INITIAL_DELAY)
261         )
262 
263         # Initialize session management functionality
264         self._session_manager = session_manager
265         if self._session_manager:
266             self.hooks.add_hook(self._session_manager)
267 
268         # Allow conversation_managers to subscribe to hooks
269         self.hooks.add_hook(self.conversation_manager)
270 
271         # Register retry strategy as a hook
272         self.hooks.add_hook(self._retry_strategy)
273 
274         self.tool_executor = tool_executor or ConcurrentToolExecutor()
275 
276         if hooks:
277             for hook in hooks:
278                 self.hooks.add_hook(hook)
279         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</original>
<patched>import strands.agent.hooks.caching as caching_hooks

    def __init__(
        self,
        model: Model | str | None = None,
        messages: Messages | None = None,
        tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,
        callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,
        trace_attributes: Mapping[str, AttributeValue] | None = None,
        *,
        agent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: AgentState | dict | None = None,
        hooks: list[HookProvider] | None = None,
        session_manager: SessionManager | None = None,
        tool_executor: ToolExecutor | None = None,
        retry_strategy: ModelRetryStrategy | None = None,
    ):
        """Initialize the Agent with the specified configuration.

        Args:
            model: Provider for running inference or a string representing the model-id for Bedrock to use.
                Defaults to strands.models.BedrockModel if None.
            messages: List of initial messages to pre-load into the conversation.
                Defaults to an empty list if None.
            tools: List of tools to make available to the agent.
                Can be specified as:

                - String tool names (e.g., "retrieve")
                - File paths (e.g., "/path/to/tool.py")
                - Imported Python modules (e.g., from strands_tools import current_time)
                - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
                - ToolProvider instances for managed tool collections
                - Functions decorated with `@strands.tool` decorator.

                If provided, only these tools will be available. If None, all tools will be available.
            system_prompt: System prompt to guide model behavior.
                Can be a string or a list of SystemContentBlock objects for advanced features like caching.
                If None, the model will behave according to its default settings.
            structured_output_model: Pydantic model type(s) for structured output.
                When specified, all agent calls will attempt to return structured output of this type.
                This can be overridden on the agent invocation.
               