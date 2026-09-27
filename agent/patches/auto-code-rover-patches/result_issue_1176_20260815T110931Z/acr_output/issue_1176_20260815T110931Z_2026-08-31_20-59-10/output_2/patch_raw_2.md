Reasoning:

The bug occurs because multiple concurrent invocations on the same Agent instance corrupt the internal state. The fix involves:

1. Adding a concurrency control primitive in the Agent class to track if an invocation is in progress. Using an `asyncio.Lock` would be suitable for async methods. Since both `invoke_async` and `stream_async` provide asynchronous APIs, a lock will ensure single concurrency.

2. Introduce a custom exception `AgentInvocationInProgress` for clear error signaling when concurrent invocations on the same agent happen.

3. Modify the async `stream_async` method to acquire the lock, reject if already locked, and release lock when done or upon error.

4. Add concurrency check in `invoke_async` since it calls `stream_async`. But because `invoke_async` awaits `stream_async` fully, it's enough to rely on locking in `stream_async` alone.

5. Add import for `asyncio`.

With this, any attempt to concurrently invoke the agent's async call will immediately raise the concurrency exception, protecting the internal state.

---

Patch:

```
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
261         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))</original>
<patched>import asyncio

89 class Agent:
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
105     class AgentInvocationInProgress(Exception):
106         """Exception raised when concurrent invocation is attempted on the same Agent instance."""
107 
108     def __init__(
109         self,
110         model: Union[Model, str, None] = None,
111         messages: Optional[Messages] = None,
112         tools: Optional[list[Union[str, dict[str, str], "ToolProvider", Any]]] = None,
113         system_prompt: Optional[str | list[SystemContentBlock]] = None,
114         structured_output_model: Optional[Type[BaseModel]] = None,
115         callback_handler: Optional[
116             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
117         ] = _DEFAULT_CALLBACK_HANDLER,
118         conversation_manager: Optional[ConversationManager] = None,
119         record_direct_tool_call: bool = True,
120         load_tools_from_directory: bool = False,
121         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
122         *,
123         agent_id: Optional[str] = None,
124         name: Optional[str] = None,
125         description: Optional[str] = None,
126         state: Optional[Union[AgentState, dict]] = None,
127         hooks: Optional[list[HookProvider]] = None,
128         session_manager: Optional[SessionManager] = None,
129         tool_executor: Optional[ToolExecutor] = None,
130     ):
131         """Initialize the Agent with the specified configuration.
132 
133         Args:
134             model: Provider for running inference or a string representing the model-id for Bedrock to use.
135                 Defaults to strands.models.BedrockModel if None.
136             messages: List of initial messages to pre-load into the conversation.
137                 Defaults to an empty list if None.
138             tools: List of tools to make available to the agent.
139                 Can be specified as:
140 
141                 - String tool names (e.g., "retrieve")
142                 - File paths (e.g., "/path/to/tool.py")
143                 - Imported Python modules (e.g., from strands_tools import current_time)
144                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
145                 - ToolProvider instances for managed tool collections
146                 - Functions decorated with `@strands.tool` decorator.
147 
148                 If provided, only these tools will be available. If None, all tools will be available.
149             system_prompt: System prompt to guide model behavior.
150                 Can be a string or a list of SystemContentBlock objects for advanced features like caching.
151                 If None, the model will behave according to its default settings.
152             structured_output_model: Pydantic model type(s) for structured output.
153                 When specified, all agent calls will attempt to return structured output of this type.
154                 This can be overridden on the agent invocation.
155                 Defaults to None (no structured output).
156             callback_handler: Callback for processing events as they happen during agent execution.
157                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
158                 If explicitly set to None, null_callback_handler is used.
159             conversation_manager: Manager for conversation history and context window.
160                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
161             record_direct_tool_call: Whether to record direct tool calls in message history.
162                 Defaults to True.
163             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
164                 Defaults to False.
165             trace_attributes: Custom trace attributes to apply to the agent's trace span.
166             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
167                 Defaults to "default".
168             name: name of the Agent
169                 Defaults to "Strands Agents".
170             description: description of what the Agent does
171                 Defaults to None.
172             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
173                 Defaults to an empty AgentState object.
174             hooks: hooks to be added to the agent hook registry
175                 Defaults to None.
176             session_manager: Manager for handling agent sessions including conversation history and state.
177                 If provided, enables session-based persistence and state management.
178             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
179 
180         Raises:
181             ValueError: If agent id contains path separators.
182         """
183         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
184         self.messages = messages if messages is not None else []
185         # initializing self._system_prompt for backwards compatibility
186         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
187         self._default_structured_output_model = structured_output_model
188         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
189         self.name = name or _DEFAULT_AGENT_NAME
190         self.description = description
191 
192         # If not provided, create a new PrintingCallbackHandler instance
193         # If explicitly set to None, use null_callback_handler
194         # Otherwise use the passed callback_handler
195         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
196         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
197             self.callback_handler = PrintingCallbackHandler()
198         elif callback_handler is None:
199             self.callback_handler = null_callback_handler
200         else:
201             self.callback_handler = callback_handler
202 
203         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
204 
205         # Process trace attributes to ensure they're of compatible types
206         self.trace_attributes: dict[str, AttributeValue] = {}
207         if trace_attributes:
208             for k, v in trace_attributes.items():
209                 if isinstance(v, (str, int, float, bool)) or (
210                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
211                 ):
212                     self.trace_attributes[k] = v
213 
214         self.record_direct_tool_call = record_direct_tool_call
215         self.load_tools_from_directory = load_tools_from_directory
216 
217         self.tool_registry = ToolRegistry()
218 
219         # Process tool list if provided
220         if tools is not None:
221             self.tool_registry.process_tools(tools)
222 
223         # Initialize tools and configuration
224         self.tool_registry.initialize_tools(self.load_tools_from_directory)
225         if load_tools_from_directory:
226             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
227 
228         self.event_loop_metrics = EventLoopMetrics()
229 
230         # Initialize tracer instance (no-op if not configured)
231         self.tracer = get_tracer()
232         self.trace_span: Optional[trace_api.Span] = None
233 
234         # Initialize agent state management
235         if state is not None:
236             if isinstance(state, dict):
237                 self.state = AgentState(state)
238             elif isinstance(state, AgentState):
239                 self.state = state
240             else:
241                 raise ValueError("state must be an AgentState object or a dict")
242         else:
243             self.state = AgentState()
244 
245         self.tool_caller = _ToolCaller(self)
246 
247         self.hooks = HookRegistry()
248 
249         self._interrupt_state = _InterruptState()
250 
251         # Initialize session management functionality
252         self._session_manager = session_manager
253         if self._session_manager:
254             self.hooks.add_hook(self._session_manager)
255 
256         # Allow conversation_managers to subscribe to hooks
257         self.hooks.add_hook(self.conversation_manager)
258 
259         self.tool_executor = tool_executor or ConcurrentToolExecutor()
260 
261         if hooks:
262             for hook in hooks:
263                 self.hooks.add_hook(hook)
264 
265         # Concurrency lock to prevent parallel invocations corrupting state
266         self._invocation_lock = asyncio.Lock()
267 
268         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>521     async def stream_async(
522         self,
523         prompt: AgentInput = None,
524         *,
525         invocation_state: dict[str, Any] | None = None,
526         structured_output_model: Type[BaseModel] | None = None,
527         **kwargs: Any,
528     ) -> AsyncIterator[Any]:
529         """Process a natural language prompt and yield events as an async iterator.
530 
531         This method provides an asynchronous interface for streaming agent events with multiple input patterns:
532         - String input: Simple text input
