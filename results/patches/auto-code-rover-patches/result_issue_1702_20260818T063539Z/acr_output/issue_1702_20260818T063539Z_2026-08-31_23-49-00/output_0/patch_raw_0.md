The main necessary changes are:

1. Add the new `ConcurrentInvocationMode` type alias using `typing.Literal` in `src/strands/types/agent.py` for consistency and reuse.
2. Add a new parameter `concurrent_invocation_mode` of type `ConcurrentInvocationMode` to `Agent.__init__` in `src/strands/agent/agent.py`, defaulting to `"throw"`. Store it on the instance as `self._concurrent_invocation_mode`. Also update the docstring to document the new parameter.
3. Modify the lock acquisition in `Agent.stream_async()` to only acquire the lock and raise `ConcurrencyException` if the mode is `"throw"`. If the mode is `"unsafe_reentrant"`, skip lock acquisition and allow concurrent calls without raising the exception, preserving all other functionality.

This minimal patch respects existing behaviors and adds the new optional concurrent invocation mode exactly as requested.

---

# modification 1
```
<file>src/strands/types/agent.py</file>
<original>1 """Agent-related type definitions for the SDK.
2 
3 This module defines the types used for an Agent.
4 """
5 
6 from typing import TypeAlias
7 
8 from .content import ContentBlock, Messages
9 from .interrupt import InterruptResponseContent
10 
11 AgentInput: TypeAlias = str | list[ContentBlock] | list[InterruptResponseContent] | Messages | None
</original>
<patched>1 """Agent-related type definitions for the SDK.
2 
3 This module defines the types used for an Agent.
4 """
5 
6 from typing import TypeAlias, Literal
7 
8 from .content import ContentBlock, Messages
9 from .interrupt import InterruptResponseContent
10 
11 AgentInput: TypeAlias = str | list[ContentBlock] | list[InterruptResponseContent] | Messages | None
12 
13 ConcurrentInvocationMode: TypeAlias = Literal["throw", "unsafe_reentrant"]
</patched>
```

# modification 2
```
<file>src/strands/agent/agent.py</file>
<original>110     def __init__(
111         self,
112         model: Model | str | None = None,
113         messages: Messages | None = None,
114         tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
115         system_prompt: str | list[SystemContentBlock] | None = None,
116         structured_output_model: type[BaseModel] | None = None,
117         callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
118         conversation_manager: ConversationManager | None = None,
119         record_direct_tool_call: bool = True,
120         load_tools_from_directory: bool = False,
121         trace_attributes: Mapping[str, AttributeValue] | None = None,
122         *,
123         agent_id: str | None = None,
124         name: str | None = None,
125         description: str | None = None,
126         state: AgentState | dict | None = None,
127         hooks: list[HookProvider] | None = None,
128         session_manager: SessionManager | None = None,
129         structured_output_prompt: str | None = None,
130         tool_executor: ToolExecutor | None = None,
131         retry_strategy: ModelRetryStrategy | _DefaultRetryStrategySentinel | None = _DEFAULT_RETRY_STRATEGY,
132     ):
133         """Initialize the Agent with the specified configuration.
134 
135         Args:
136             model: Provider for running inference or a string representing the model-id for Bedrock to use.
137                 Defaults to strands.models.BedrockModel if None.
138             messages: List of initial messages to pre-load into the conversation.
139                 Defaults to an empty list if None.
140             tools: List of tools to make available to the agent.
141                 Can be specified as:
142 
143                 - String tool names (e.g., "retrieve")
144                 - File paths (e.g., "/path/to/tool.py")
145                 - Imported Python modules (e.g., from strands_tools import current_time)
146                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
147                 - ToolProvider instances for managed tool collections
148                 - Functions decorated with `@strands.tool` decorator.
149 
150                 If provided, only these tools will be available. If None, all tools will be available.
151             system_prompt: System prompt to guide model behavior.
152                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
153                 If None, the model will behave according to its default settings.
154             structured_output_model: Pydantic model type(s) for structured output.
155                 When specified, all agent calls will attempt to return structured output of this type.
156                 This can be overridden on the agent invocation.
157                 Defaults to None (no structured output).
158             callback_handler: Callback for processing events as they happen during agent execution.
159                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
160                 If explicitly set to None, null_callback_handler is used.
161             conversation_manager: Manager for conversation history and context window.
162                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
163             record_direct_tool_call: Whether to record direct tool calls in message history.
164                 Defaults to True.
165             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
166                 Defaults to False.
167             trace_attributes: Custom trace attributes to apply to the agent's trace span.
168             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
169                 Defaults to "default".
170             name: name of the Agent
171                 Defaults to "Strands Agents".
172             description: description of what the Agent does
173                 Defaults to None.
174             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
175                 Defaults to an empty AgentState object.
176             hooks: hooks to be added to the agent hook registry
177                 Defaults to None.
178             session_manager: Manager for handling agent sessions including conversation history and state.
179                 If provided, enables session-based persistence and state management.
180             structured_output_prompt: Custom prompt message used when forcing structured output.
181                 When using structured output, if the model doesn't automatically use the output tool,
182                 the agent sends a follow-up message to request structured formatting. This parameter
183                 allows customizing that message.
184                 Defaults to "You must format the previous response as structured output."
185             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
186             retry_strategy: Strategy for retrying model calls on throttling or other transient errors.
187                 Defaults to ModelRetryStrategy with max_attempts=6, initial_delay=4s, max_delay=240s.
188                 Implement a custom HookProvider for custom retry logic, or pass None to disable retries.
189 
190         Raises:
191             ValueError: If agent id contains path separators.
192         """
193         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
194         self.messages = messages if messages is not None else []
195         # initializing self._system_prompt for backwards compatibility
196         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
197         self._default_structured_output_model = structured_output_model
198         self._structured_output_prompt = structured_output_prompt
199         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
200         self.name = name or _DEFAULT_AGENT_NAME
201         self.description = description
202 
203         # If not provided, create a new PrintingCallbackHandler instance
204         # If explicitly set to None, use null_callback_handler
205         # Otherwise use the passed callback_handler
206         self.callback_handler: Callable[..., Any] | PrintingCallbackHandler
207         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
208             self.callback_handler = PrintingCallbackHandler()
209         elif callback_handler is None:
210             self.callback_handler = null_callback_handler
211         else:
212             self.callback_handler = callback_handler
213 
214         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
215 
216         # Process trace attributes to ensure they're of compatible types
217         self.trace_attributes: dict[str, AttributeValue] = {}
218         if trace_attributes:
219             for k, v in trace_attributes.items():
220                 if isinstance(v, (str, int, float, bool)) or (
221                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
222                 ):
223                     self.trace_attributes[k] = v
224 
225         self.record_direct_tool_call = record_direct_tool_call
226         self.load_tools_from_directory = load_tools_from_directory
227 
228         self.tool_registry = ToolRegistry()
229 
230         # Process tool list if provided
231         if tools is not None:
232             self.tool_registry.process_tools(tools)
233 
234         # Initialize tools and configuration
235         self.tool_registry.initialize_tools(self.load_tools_from_directory)
236         if load_tools_from_directory:
237             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
238 
239         self.event_loop_metrics = EventLoopMetrics()
240 
241         # Initialize tracer instance (no-op if not configured)
242         self.tracer = get_tracer()
243         self.trace_span: trace_api.Span | None = None
244 
245         # Initialize agent state management
246         if state is not None:
247             if isinstance(state, dict):
248                 self.state = AgentState(state)
249             elif isinstance(state, AgentState):
250                 self.state = state
251             else:
252                 raise ValueError("state must be an AgentState object or a dict")
253         else:
254             self.state = AgentState()
255 
256         self.tool_caller = _ToolCaller(self)
257 
258         self.hooks = HookRegistry()
259 
260         self._interrupt_state = _InterruptState()
261 
262         # Initialize lock for guarding concurrent invocations
263         # Using threading.Lock instead of asyncio.Lock because run_async() creates
264         # separate event loops in different threads, so asyncio.Lock wouldn't work
265         self._invocation_lock = threading.Lock()
266 
267         # In the future, we'll have a RetryStrategy base class but until
268         # that API is determined we only allow ModelRetryStrategy
269         if (
270             retry_strategy is not None
271             and not isinstance(retry_strategy, _DefaultRetryStrategySentinel)
272             and type(retry_strategy) is not ModelRetryStrategy
273         ):
274             raise ValueError("retry_strategy must be an instance of ModelRetryStrategy")
275 
276         # If not provided (using the default), create a new ModelRetryStrategy instance
277         # If explicitly set to None, disable retries (max_attempts=1 means no retries)
278         # Otherwise use the passed retry_strategy
279         if isinstance(retry_strategy, _DefaultRetryStrategySentinel):
280             self._retry_strategy = ModelRetryStrategy(
281                 max_attempts=MAX_ATTEMPTS, max_delay=MAX_DELAY, initial_delay=INITIAL_DELAY
282             )
283         elif retry_strategy is None:
284             # If no retry strategy is passed in, then we turn retries off
285             self._retry_strategy = ModelRetryStrategy(max_attempts=1)
286         else:
287             self._retry_strategy = retry_strategy
288 
289         # Initialize session management functionality
290         self._session_manager = session_manager
291         if self._session_manager:
292             self.hooks.add_hook(self._session_manager)
293 
294         # Allow conversation_managers to subscribe to hooks
295         self.hooks.add_hook(self.conversation_manager)
296 
297         # Register retry strategy as a hook
298         self.hooks.add_hook(self._retry_strategy)
299 
300         self.tool_executor = tool_executor or ConcurrentToolExecutor()
301 
302         if hooks:
303             for hook in hooks:
304                 self.hooks.add_hook(hook)
305         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</original>
<patched>110     def __init__(
111         self,
112         model: Model | str | None = None,
113         messages: Messages | None = None,
114         tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
115         system_prompt: str | list[SystemContentBlock] | None = None,
116         structured_output_model: type[BaseModel] | None = None,
117         callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
118         conversation_manager: ConversationManager | None = None,
119         record_direct_tool_call: bool = True,
120         load_tools_from_directory: bool = False,
121         trace_attributes: Mapping[str, AttributeValue] | None = None,
122         *,
123         agent_id: str | None = None,
124         name: str | None = None,
125         description: str | None = None,
126         state: AgentState | dict | None = None,
127         hooks: list[HookProvider] | None = None,
128         session_manager: SessionManager | None = None,
129         structured_output_prompt: str | None = None,
130         tool_executor: ToolExecutor | None = None,
131         retry_strategy: ModelRetryStrategy | _DefaultRetryStrategySentinel | None = _DEFAULT_RETRY_STRATEGY,
132         concurrent_invocation_mode: "ConcurrentInvocationMode" = "throw",
133     ):
134         """Initialize the Agent with the specified configuration.
135 
136         Args:
137             model: Provider for running inference or a string representing the model-id for Bedrock to use.
138                 Defaults to strands.models.BedrockModel if None.
139             messages: List of initial messages to pre-load into the conversation.
140                 Defaults to an empty list if None.
141             tools: List of tools to make available to the agent.
142                 Can be specified as:
143 
144                 - String tool names (e.g., "retrieve")
145                 - File paths (e.g., "/path/to/tool.py")
146                 - Imported Python modules (e.g., from strands_tools import current_time)
147                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
148                 - ToolProvider instances for managed tool collections
149                 - Functions decorated with `@strands.tool` decorator.
150 
151                 If provided, only these tools will be available. If None, all tools will be available.
152             system_prompt: System prompt to guide model behavior.
153                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
154                 If None, the model will behave according to its default settings.
155             structured_output_model: Pydantic model type(s) for structured output.
156                 When specified, all agent calls will attempt to return structured output of this type.
157                 This can be overridden on the agent invocation.
158                 Defaults to None (no structured output).
159             callback_handler: Callback for processing events as they happen during agent execution.
160                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
161                 If explicitly set to None, null_callback_handler is used.
162             conversation_manager: Manager for conversation history and context window.
163                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
164             record_direct_tool_call: Whether to record direct tool calls in message history.
165                 Defaults to True.
166             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
167                 Defaults to False.
168             trace_attributes: Custom trace attributes to apply to the agent's trace span.
169             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
170                 Defaults to "default".
171             name: name of the Agent
172                 Defaults to "Strands Agents".
173             description: description of what the Agent does
174                 Defaults to None.
175             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
176                 Defaults to an empty AgentState object.
177             hooks: hooks to be added to the agent hook registry
178                 Defaults to None.
179             session_manager: Manager for handling agent sessions including conversation history and state.
180                 If provided, enables session-based persistence and state management.
181             structured_output_prompt: Custom prompt message used when forcing structured output.
182                 When using structured output, if the model doesn't automatically use the output tool,
183                 the agent sends a follow-up message to request structured formatting. This parameter
184                 allows customizing that message.
185                 Defaults to "You must format the previous response as structured output."
186             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
187             retry_strategy: Strategy for retrying model calls on throttling or other transient errors.
188                 Defaults to ModelRetryStrategy with max_attempts=6, initial_delay=4s, max_delay=240s.
189                 Implement a custom HookProvider for custom retry logic, or pass None to disable retries.
190             concurrent_invocation_mode: Controls behavior on concurrent invocations to the same agent instance.
191                 Values:
192                     "throw": (default) Raises ConcurrencyException on concurrent invocation.
193                     "unsafe_reentrant": Skips lock and allows concurrent invocations (unsafe).
194 
195         Raises:
196             ValueError: If agent id contains path separators.
197         """
198         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
199         self.messages = messages if messages is not None else []
200         # initializing self._system_prompt for backwards compatibility
201         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
202         self._default_structured_output_model = structured_output_model
203         self._structured_output_prompt = structured_output_prompt
204         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
205         self.name = name or _DEFAULT_AGENT_NAME
206         self.description = description
207 
208         # If not provided, create a new PrintingCallbackHandler instance
209         # If explicitly set to None, use null_callback_handler
210         # Otherwise use the passed callback_handler
211         self.callback_handler: Callable[..., Any] | PrintingCallbackHandler
212         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
213             self.callback_handler = PrintingCallbackHandler()
214         elif callback_handler is None:
215             self.callback_handler = null_callback_handler
216         else:
217             self.callback_handler = callback_handler
218 
219         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
220 
221         # Process trace attributes to ensure they're of compatible types
222