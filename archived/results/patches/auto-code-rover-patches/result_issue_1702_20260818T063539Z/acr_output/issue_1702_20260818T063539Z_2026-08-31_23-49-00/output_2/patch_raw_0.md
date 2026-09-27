Reasoning:

1. We need to add the new `concurrent_invocation_mode` parameter with type `ConcurrentInvocationMode` (a Literal) to the Agent constructor. The default will be `"throw"` to maintain backward compatibility.
2. This parameter should be stored as `self._concurrent_invocation_mode`.
3. Update the docstring of the constructor to document this parameter.
4. Modify the locking logic in `stream_async()` to conditionally skip acquiring the lock if `concurrent_invocation_mode` is set to `"unsafe_reentrant"`. If it is `"throw"` (default), the current behavior remains (acquire lock, raise `ConcurrencyException` if unable to acquire).
5. Add the required import of `Literal` and define the `ConcurrentInvocationMode` alias in `src/strands/types/agent.py`.
6. Import `ConcurrentInvocationMode` into `src/strands/agent/agent.py` for typing.
7. These changes are minimal and backward compatible.
8. No runtime warnings are to be added for unsafe mode as per requirements.

Patch:

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

```
<file>src/strands/agent/agent.py</file>
<original>94 class Agent(AgentBase):
95     """Core Agent implementation.
96 
97     An agent orchestrates the following workflow:
98 
99     1. Receives user input
100     2. Processes the input using a language model
101     3. Decides whether to use tools to gather information or perform actions
102     4. Executes those tools and receives results
103     5. Continues reasoning with the new information
104     6. Produces a final response
105     """
106 
107     # For backwards compatibility
108     ToolCaller = _ToolCaller
109 
110     def __init__(
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
306 
307     @property
308     def system_prompt(self) -> str | None:
309         """Get the system prompt as a string for backwards compatibility.
310 
311         Returns the system prompt as a concatenated string when it contains text content,
312         or None if no text content is present. This maintains backwards compatibility
313         with existing code that expects system_prompt to be a string.
314 
315         Returns:
316             The system prompt as a string, or None if no text content exists.
317         """
318         return self._system_prompt
319 
320     @system_prompt.setter
321     def system_prompt(self, value: str | list[SystemContentBlock] | None) -> None:
322         """Set the system prompt and update internal content representation.
323 
324         Accepts either a string or list of SystemContentBlock objects.
325         When set, both the backwards-compatible string representation and the internal
326         content block representation are updated to maintain consistency.
327 
328         Args:
329             value: System prompt as string, list of SystemContentBlock objects, or None.
330                   - str: Simple text prompt (most common use case)
331                   - list[SystemContentBlock]: Content blocks with features like caching
332                   - None: Clear the system prompt
333         """
334         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(value)
335 
336     @property
337     def tool(self) -> _ToolCaller:
338         """Call tool as a function.
339 
340         Returns:
341             Tool caller through which user can invoke tool as a function.
342 
343         Example:
344             ```
345             agent = Agent(tools=[calculator])
346             agent.tool.calculator(...)
347             ```
348         """
349         return self.tool_caller
350 
351     @property
352     def tool_names(self) -> list[str]:
353         """Get a list of all registered tool names.
354 
355         Returns:
356             Names of all tools available to this agent.
357         """
358         all_tools = self.tool_registry.get_all_tools_config()
359         return list(all_tools.keys())
360 
361     def __call__(
362         self,
363         prompt: AgentInput = None,
364         *,
365         invocation_state: dict[str, Any] | None = None,
366         structured_output_model: type[BaseModel] | None = None,
367         structured_output_prompt: str | None = None,
368         **kwargs: Any,
369     ) -> AgentResult:
370         """Process a natural language prompt through the agent's event loop.
371 
372         This method implements the conversational interface with multiple input patterns:
373         - String input: `agent("hello!")`
374         - ContentBlock list: `agent([{"text": "hello"}, {"image": {...}}])`
375         - Message list: `agent([{"role": "user", "content": [{"text": "hello"}]}])`
376         - No input: `agent()` - uses existing conversation history
377 
378         Args:
379             prompt: User input in various formats:
380                 - str: Simple text input
381                 - list[ContentBlock]: Multi-modal content blocks
382                 - list[Message]: Complete messages with roles
383                 - None: Use existing conversation history
384             invocation_state: Additional parameters to pass through the event loop.
385             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
386             structured_output_prompt: Custom prompt for forcing structured output (overrides agent default).
387             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
388 
389         Returns:
390             Result object containing:
391 
392                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
393                 - message: The final message from the model
394                 - metrics: Performance metrics from the event loop
395                 - state: The final state of the event loop
396                 - structured_output: Parsed structured output when structured_output_model was specified
397         """
398         return run_async(
399             lambda: self.invoke_async(
400                 prompt,
401                 invocation_state=invocation_state,
402                 structured_output_model=structured_output_model,
403                 structured_output_prompt=structured_output_prompt,
404                 **kwargs,
405             )
406         )
407 
408     async def invoke_async(
409         self,
410         prompt: AgentInput = None,
411         *,
412         invocation_state: dict[str, Any] | None = None,
413         structured_output_model: type[BaseModel] | None = None,
414         structured_output_prompt: str | None = None,
415         **kwargs: Any,
416     ) -> AgentResult:
417         """Process a natural language prompt through the agent's event loop.
418 
419         This method implements the conversational interface with multiple input patterns:
420         - String input: Simple text input
421         - ContentBlock list: Multi-modal content blocks
422         - Message list: Complete messages with roles
423         - No input: Use existing conversation history
424 
425         Args:
426             prompt: User input in various formats:
427                 - str: Simple text input
428                 - list[ContentBlock]: Multi-modal content blocks
429                 - list[Message]: Complete messages with roles
430                 - None: Use existing conversation history
431             invocation_state: Additional parameters to pass through the event loop.
432             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
433             structured_output_prompt: Custom prompt for forcing structured output (overrides agent default).
434             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
435 
436         Returns:
437             Result: object containing:
438 
439                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
440                 - message: The final message from the model
441                 - metrics: Performance metrics from the event loop
442                 - state: The final state of the event loop
443         """
444         events = self.stream_async(
445             prompt,
446             invocation_state=