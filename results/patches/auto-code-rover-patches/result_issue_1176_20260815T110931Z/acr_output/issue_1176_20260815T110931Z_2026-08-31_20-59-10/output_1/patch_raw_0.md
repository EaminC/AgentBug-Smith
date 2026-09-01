Reasoning:

To fix the issue of corrupted state due to parallel invocations on the same Agent instance, we need to implement concurrency control that prevents concurrent invocations.

- First, in `__init__`, add an `asyncio.Lock` called `_invocation_lock` to be used for concurrency control.
- Then, in `invoke_async`, check if the lock is already acquired meaning an invocation is ongoing:
  - If yes, raise a clear concurrency error.
  - If not, acquire the lock for the duration of the invocation, ensuring no overlapping invocations happen concurrently.
- This will stop overlapping calls corrupting the agent's internal state.

No changes to other methods are required as the lock mechanism protects the main asynchronous invocation method.

---

Patch:

```
<file>src/strands/agent/agent.py</file>
<original>105     def __init__(
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
</original>
<patched>105     import asyncio
106 
107     def __init__(
108         self,
109         model: Union[Model, str, None] = None,
110         messages: Optional[Messages] = None,
111         tools: Optional[list[Union[str, dict[str, str], "ToolProvider", Any]]] = None,
112         system_prompt: Optional[str | list[SystemContentBlock]] = None,
113         structured_output_model: Optional[Type[BaseModel]] = None,
114         callback_handler: Optional[
115             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
116         ] = _DEFAULT_CALLBACK_HANDLER,
117         conversation_manager: Optional[ConversationManager] = None,
118         record_direct_tool_call: bool = True,
119         load_tools_from_directory: bool = False,
120         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
121         *,
122         agent_id: Optional[str] = None,
123         name: Optional[str] = None,
124         description: Optional[str] = None,
125         state: Optional[Union[AgentState, dict]] = None,
126         hooks: Optional[list[HookProvider]] = None,
127         session_manager: Optional[SessionManager] = None,
128         tool_executor: Optional[ToolExecutor] = None,
129     ):
130         """Initialize the Agent with the specified configuration.
131 
132         Args:
133             model: Provider for running inference or a string representing the model-id for Bedrock to use.
134                 Defaults to strands.models.BedrockModel if None.
135             messages: List of initial messages to pre-load into the conversation.
136                 Defaults to an empty list if None.
137             tools: List of tools to make available to the agent.
138                 Can be specified as:
139 
140                 - String tool names (e.g., "retrieve")
141                 - File paths (e.g., "/path/to/tool.py")
142                 - Imported Python modules (e.g., from strands_tools import current_time)
143                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
144                 - ToolProvider instances for managed tool collections
145                 - Functions decorated with `@strands.tool` decorator.
146 
147                 If provided, only these tools will be available. If None, all tools will be available.
148             system_prompt: System prompt to guide model behavior.
149                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
150                 If None, the model will behave according to its default settings.
151             structured_output_model: Pydantic model type(s) for structured output.
152                 When specified, all agent calls will attempt to return structured output of this type.
153                 This can be overridden on the agent invocation.
154                 Defaults to None (no structured output).
155             callback_handler: Callback for processing events as they happen during agent execution.
156                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
157                 If explicitly set to None, null_callback_handler is used.
158             conversation_manager: Manager for conversation history and context window.
159                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
160             record_direct_tool_call: Whether to record direct tool calls in message history.
161                 Defaults to True.
162             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
163                 Defaults to False.
164             trace_attributes: Custom trace attributes to apply to the agent's trace span.
165             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
166                 Defaults to "default".
167             name: name of the Agent
168                 Defaults to "Strands Agents".
169             description: description of what the Agent does
170                 Defaults to None.
171             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
172                 Defaults to an empty AgentState object.
173             hooks: hooks to be added to the agent hook registry
174                 Defaults to None.
175             session_manager: Manager for handling agent sessions including conversation history and state.
176                 If provided, enables session-based persistence and state management.
177             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
178 
179         Raises:
180             ValueError: If agent id contains path separators.
181         """
182         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
183         self.messages = messages if messages is not None else []
184         # initializing self._system_prompt for backwards compatibility
185         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
186         self._default_structured_output_model = structured_output_model
187         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
188         self.name = name or _DEFAULT_AGENT_NAME
189         self.description = description
190 
191         # If not provided, create a new PrintingCallbackHandler instance
192         # If explicitly set to None, use null_callback_handler
193         # Otherwise use the passed callback_handler
194         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
195         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
196             self.callback_handler = PrintingCallbackHandler()
197         elif callback_handler is None:
198             self.callback_handler = null_callback_handler
199         else:
200             self.callback_handler = callback_handler
201 
202         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
203 
204         # Process trace attributes to ensure they're of compatible types
205         self.trace_attributes: dict[str, AttributeValue] = {}
206         if trace_attributes:
207             for k, v in trace_attributes.items():
208                 if isinstance(v, (str, int, float, bool)) or (
209                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
210                 ):
211                     self.trace_attributes[k] = v
212 
213         self.record_direct_tool_call = record_direct_tool_call
214         self.load_tools_from_directory = load_tools_from_directory
215 
216         self.tool_registry = ToolRegistry()
217 
218         # Process tool list if provided
219         if tools is not None:
220             self.tool_registry.process_tools(tools)
221 
222         # Initialize tools and configuration
223         self.tool_registry.initialize_tools(self.load_tools_from_directory)
224         if load_tools_from_directory:
225             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
226 
227         self.event_loop_metrics = EventLoopMetrics()
228 
229         # Initialize tracer instance (no-op if not configured)
230         self.tracer = get_tracer()
231         self.trace_span: Optional[trace_api.Span] = None
232 
233         # Initialize agent state management
234         if state is not None:
235             if isinstance(state, dict):
236                 self.state = AgentState(state)
237             elif isinstance(state, AgentState):
238                 self.state = state
239             else:
240                 raise ValueError("state must be an AgentState object or a dict")
241         else:
242             self.state = AgentState()
243 
244         self.tool_caller = _ToolCaller(self)
245 
246         self.hooks = HookRegistry()
247 
248         self._interrupt_state = _InterruptState()
249 
250         # Initialize session management functionality
251         self._session_manager = session_manager
252         if self._session_manager:
253             self.hooks.add_hook(self._session_manager)
254 
255         # Allow conversation_managers to subscribe to hooks
256         self.hooks.add_hook(self.conversation_manager)
257 
258         self.tool_executor = tool_executor or ConcurrentToolExecutor()
259 
260         # Add a lock to control concurrent invocation access
261         self._invocation_lock = asyncio.Lock()
262 
263         if hooks:
264             for hook in hooks:
265                 self.hooks.add_hook(hook)
266         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>358     async def invoke_async(
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
398         return cast(AgentResult, event["result"])</original>
<patched>358     async def invoke_async(
359         self,
360         prompt: AgentInput = None,
361         *,
362         invocation_state: dict[str, Any] | None = None,
363         structured_output_model: Type[BaseModel] | None = None,
364        