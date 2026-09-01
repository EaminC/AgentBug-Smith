Reasoning:

The issue is about parallel invocations on the same Agent instance corrupting the internal state. To fix this, we should ensure that only one invocation can run at a time on an Agent instance.

We can use an asyncio lock to block concurrent asynchronous invocations. If a concurrent call is attempted, instead of waiting, we raise a concurrency exception immediately.

Changes to implement:

1. In the `Agent.__init__` method, initialize an asyncio.Lock named, for example, `_invocation_lock`.

2. Modify the asynchronous method `invoke_async` to acquire the lock in a non-blocking manner at the start of the method. If the lock is already held (meaning the agent is busy), raise a concurrency exception immediately.

3. Make sure the lock is released after invocation finishes, whether successfully or by exception.

4. Define a new exception class, `InvocationConcurrencyError`, for this concurrency failure.

5. Modify the synchronous call `__call__` so that when it calls `invoke_async` it properly propagates this concurrency exception to the caller.

This approach ensures that any simultaneous invocation attempt on the same agent will fail fast, protecting the internal state.

---

Patch start:

```python
<file>src/strands/agent/agent.py</file>
<original>89 class Agent:
90     """Core Agent implementation.
91 
92     An agent orchestrates the following workflow:
93 
94     1. Receives user input
95     2. Processes the input using a language model
96     3. Decides whether to use tools to gather information or perform actions
97     4. Executes those tools and receives results
98     5. Continues reasoning with the new information
99     6. Produces a final response
100     """
101 
102     # For backwards compatibility
103     ToolCaller = _ToolCaller
104 
105     def __init__(
106         self,
107         model: Union[Model, str, None] = None,
108         messages: Optional[Messages] = None,
109         tools: Optional[list[Union[str, dict[str, str], "ToolProvider", Any]]] = None,
110         system_prompt: Optional[str | list[SystemContentBlock]] = None,
111         structured_output_model: Optional[Type[BaseModel]] = None,
112         callback_handler: Optional[
113             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
114         ] = _DEFAULT_CALLBACK_HANDLER,
115         conversation_manager: Optional[ConversationManager] = None,
116         record_direct_tool_call: bool = True,
117         load_tools_from_directory: bool = False,
118         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
119         *,
120         agent_id: Optional[str] = None,
121         name: Optional[str] = None,
122         description: Optional[str] = None,
123         state: Optional[Union[AgentState, dict]] = None,
124         hooks: Optional[list[HookProvider]] = None,
125         session_manager: Optional[SessionManager] = None,
126         tool_executor: Optional[ToolExecutor] = None,
127     ):
128         """Initialize the Agent with the specified configuration.
129 
130         Args:
131             model: Provider for running inference or a string representing the model-id for Bedrock to use.
132                 Defaults to strands.models.BedrockModel if None.
133             messages: List of initial messages to pre-load into the conversation.
134                 Defaults to an empty list if None.
135             tools: List of tools to make available to the agent.
136                 Can be specified as:
137 
138                 - String tool names (e.g., "retrieve")
139                 - File paths (e.g., "/path/to/tool.py")
140                 - Imported Python modules (e.g., from strands_tools import current_time)
141                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
142                 - ToolProvider instances for managed tool collections
143                 - Functions decorated with `@strands.tool` decorator.
144 
145                 If provided, only these tools will be available. If None, all tools will be available.
146             system_prompt: System prompt to guide model behavior.
147                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
148                 If None, the model will behave according to its default settings.
149             structured_output_model: Pydantic model type(s) for structured output.
150                 When specified, all agent calls will attempt to return structured output of this type.
151                 This can be overridden on the agent invocation.
152                 Defaults to None (no structured output).
153             callback_handler: Callback for processing events as they happen during agent execution.
154                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
155                 If explicitly set to None, null_callback_handler is used.
156             conversation_manager: Manager for conversation history and context window.
157                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
158             record_direct_tool_call: Whether to record direct tool calls in message history.
159                 Defaults to True.
160             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
161                 Defaults to False.
162             trace_attributes: Custom trace attributes to apply to the agent's trace span.
163             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
164                 Defaults to "default".
165             name: name of the Agent
166                 Defaults to "Strands Agents".
167             description: description of what the Agent does
168                 Defaults to None.
169             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
170                 Defaults to an empty AgentState object.
171             hooks: hooks to be added to the agent hook registry
172                 Defaults to None.
173             session_manager: Manager for handling agent sessions including conversation history and state.
174                 If provided, enables session-based persistence and state management.
175             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
176 
177         Raises:
178             ValueError: If agent id contains path separators.
179         """
180         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
181         self.messages = messages if messages is not None else []
182         # initializing self._system_prompt for backwards compatibility
183         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
184         self._default_structured_output_model = structured_output_model
185         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
186         self.name = name or _DEFAULT_AGENT_NAME
187         self.description = description
188 
189         # If not provided, create a new PrintingCallbackHandler instance
190         # If explicitly set to None, use null_callback_handler
191         # Otherwise use the passed callback_handler
192         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
193         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
194             self.callback_handler = PrintingCallbackHandler()
195         elif callback_handler is None:
196             self.callback_handler = null_callback_handler
197         else:
198             self.callback_handler = callback_handler
199 
200         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
201 
202         # Process trace attributes to ensure they're of compatible types
203         self.trace_attributes: dict[str, AttributeValue] = {}
204         if trace_attributes:
205             for k, v in trace_attributes.items():
206                 if isinstance(v, (str, int, float, bool)) or (
207                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
208                 ):
209                     self.trace_attributes[k] = v
210 
211         self.record_direct_tool_call = record_direct_tool_call
212         self.load_tools_from_directory = load_tools_from_directory
213 
214         self.tool_registry = ToolRegistry()
215 
216         # Process tool list if provided
217         if tools is not None:
218             self.tool_registry.process_tools(tools)
219 
220         # Initialize tools and configuration
221         self.tool_registry.initialize_tools(self.load_tools_from_directory)
222         if load_tools_from_directory:
223             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
224 
225         self.event_loop_metrics = EventLoopMetrics()
226 
227         # Initialize tracer instance (no-op if not configured)
228         self.tracer = get_tracer()
229         self.trace_span: Optional[trace_api.Span] = None
230 
231         # Initialize agent state management
232         if state is not None:
233             if isinstance(state, dict):
234                 self.state = AgentState(state)
235             elif isinstance(state, AgentState):
236                 self.state = state
237             else:
238                 raise ValueError("state must be an AgentState object or a dict")
239         else:
240             self.state = AgentState()
241 
242         self.tool_caller = _ToolCaller(self)
243 
244         self.hooks = HookRegistry()
245 
246         self._interrupt_state = _InterruptState()
247 
248         # Initialize session management functionality
249         self._session_manager = session_manager
250         if self._session_manager:
251             self.hooks.add_hook(self._session_manager)
252 
253         # Allow conversation_managers to subscribe to hooks
254         self.hooks.add_hook(self.conversation_manager)
255 
256         self.tool_executor = tool_executor or ConcurrentToolExecutor()
257 
258         if hooks:
259             for hook in hooks:
260                 self.hooks.add_hook(hook)
261         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
262 
263     @property
264     def system_prompt(self) -> str | None:
265         """Get the system prompt as a string for backwards compatibility.
266 
267         Returns the system prompt as a concatenated string when it contains text content,
268         or None if no text content is present. This maintains backwards compatibility
269         with existing code that expects system_prompt to be a string.
270 
271         Returns:
272             The system prompt as a string, or None if no text content exists.
273         """
274         return self._system_prompt
275 
276     @system_prompt.setter
277     def system_prompt(self, value: str | list[SystemContentBlock] | None) -> None:
278         """Set the system prompt and update internal content representation.
279 
280         Accepts either a string or list of SystemContentBlock objects.
281         When set, both the backwards-compatible string representation and the internal
282         content block representation are updated to maintain consistency.
283 
284         Args:
285             value: System prompt as string, list of SystemContentBlock objects, or None.
286                   - str: Simple text prompt (most common use case)
287                   - list[SystemContentBlock]: Content blocks with features like caching
288                   - None: Clear the system prompt
289         """
290         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(value)
291 
292     @property
293     def tool(self) -> _ToolCaller:
294         """Call tool as a function.
295 
296         Returns:
297             Tool caller through which user can invoke tool as a function.
298 
299         Example:
300             ```
301             agent = Agent(tools=[calculator])
302             agent.tool.calculator(...)
303             ```
304         """
305         return self.tool_caller
306 
307     @property
308     def tool_names(self) -> list[str]:
309         """Get a list of all registered tool names.
310 
311         Returns:
312             Names of all tools available to this agent.
313         """
314         all_tools = self.tool_registry.get_all_tools_config()
315         return list(all_tools.keys())
316 
317     def __call__(
318         self,
319         prompt: AgentInput = None,
320         *,
321         invocation_state: dict[str, Any] | None = None,
322         structured_output_model: Type[BaseModel] | None = None,
323         **kwargs: Any,
324     ) -> AgentResult:
325         """Process a natural language prompt through the agent's event loop.
326 
327         This method implements the conversational interface with multiple input patterns:
328         - String input: `agent("hello!")`
329         - ContentBlock list: `agent([{"text": "hello"}, {"image": {...}}])`
330         - Message list: `agent([{"role": "user", "content": [{"text": "hello"}]}])`
331         - No input: `agent()` - uses existing conversation history
332 
333         Args:
334             prompt: User input in various formats:
335                 - str: Simple text input
336                 - list[ContentBlock]: Multi-modal content blocks
337                 - list[Message]: Complete messages with roles
338                 - None: Use existing conversation history
339             invocation_state: Additional parameters to pass through the event loop.
340             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
341             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
342 
343         Returns:
344             Result object containing:
345 
346                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
347                 - message: The final message from the model
348                 - metrics: Performance metrics from the event loop
349                 - state: The final state of the event loop
350                 - structured_output: Parsed structured output when structured_output_model was specified
351         """
352         return run_async(
353             lambda: self.invoke_async(
354                 prompt, invocation_state=invocation_state, structured_output_model=structured_output_model, **kwargs
355             )
356         )
357 
358     async def invoke_async(
359         self,
360         prompt: AgentInput = None,
361         *,
362         invocation_state: dict[str, Any] | None = None,
363         structured_output_model: Type[BaseModel] | None = None,
364         **kwargs: Any,
365     ) -> AgentResult:
366         """Process a natural language prompt through the agent's event loop.
367 
368         This method implements the conversational interface with multiple input patterns:
369         - String input: Simple text input
370         - ContentBlock list: Multi-modal content blocks
371         - Message list: Complete messages with roles
372         - No input: Use existing conversation history
373 
374         Args:
375             prompt: User input in various formats:
376                 - str: Simple text input
377                 - list[ContentBlock]: Multi-modal content blocks
378                 - list[Message]: Complete messages with roles
379                 - None: Use existing conversation history
380             invocation_state: Additional parameters to pass through the event loop.
381             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
382             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
383 
384         Returns:
385             Result: object containing:
386 
387                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
388                 - message: The final message from the model
389                 - metrics: Performance metrics from the event loop
390                 - state: The final state of the event loop
391         """
392         events = self.stream_async(
393             prompt, invocation_state=invocation_state, structured_output_model=structured_output_model, **kwargs
394         )
395         async for event in events:
396             _ = event
397 
398         return cast(AgentResult, event["result"])
399 
400     def structured_output(self, output_model: Type[T], prompt: AgentInput = None) -> T:
401         """This method allows you to get structured output from the agent.
402 
403         If you pass in a prompt, it will be used temporarily without adding it to the conversation history.
404         If you don't pass in a prompt, it will use only the existing conversation history to respond.
405 
406         For smaller models, you may want to use the optional prompt to add additional instructions to explicitly
407         instruct the model to output the structured data.
408 
409         Args:
410             output_model: The output model (a JSON schema written as a Pydantic BaseModel)
411                 that the agent will use when responding.
412             prompt: The prompt to use for the agent in various formats:
413                 - str: Simple text input
414                 - list[ContentBlock]: Multi-modal content blocks
415                 - list[Message]: Complete messages with roles
416                 - None: Use existing conversation history
417 
418         Raises:
419             ValueError: If no conversation history or prompt is provided.
420         """
421         warnings.warn(
422             "Agent.structured_output method is deprecated."
423             " You should pass in `structured_output_model` directly into the agent invocation."
424             " see: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/structured-output/",
425             category=DeprecationWarning,
426             stacklevel=2,
427         )
428 
429         return run_async(lambda: self.structured_output_async(output_model, prompt))
430 
431     async def structured_output_async(self, output_model: Type[T], prompt: AgentInput = None) -> T:
432         """This method allows you to get structured output from the agent.
433 
434         If you pass in a prompt, it will be used temporarily without adding it to the conversation history.
435         If you don't pass in a prompt, it will use only the existing conversation history to respond.
436 
437         For smaller models, you may want to use the optional prompt to add additional instructions to explicitly
438         instruct the model to output the structured data.
439 
440         Args:
441             output_model: The output model (a JSON schema written as a Pydantic BaseModel)
442                 that the agent will use when responding.
443             prompt: The prompt to use for the agent (will not be added to conversation history).
444 
445         Raises:
446             ValueError: If no conversation history or prompt is provided.
447         -
448         """
449         if self._interrupt_state.activated:
450             raise RuntimeError("cannot call structured output during interrupt")
451 
452         warnings.warn(
453             "Agent.structured_output_async method is deprecated."
454             " You should pass in `structured_output_model` directly into the agent invocation."
455             " see: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/structured-output/",
456             category=DeprecationWarning,
457             stacklevel=2,
458         )
459         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self))
460         with self.tracer.tracer.start_as_current_span(
461             "execute_structured_output", kind=trace_api.SpanKind.CLIENT
462         ) as structured_output_span:
463             try:
464                 if not self.messages and not prompt:
465                     raise ValueError("No conversation history or prompt provided")
466 
467                 temp_messages: Messages = self.messages