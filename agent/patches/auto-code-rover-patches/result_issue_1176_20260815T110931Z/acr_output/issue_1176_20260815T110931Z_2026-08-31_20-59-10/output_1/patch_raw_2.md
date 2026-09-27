Reasoning:
To prevent concurrent invocations of the same Agent instance from corrupting internal state, we need to ensure only one invocation runs at a time. The best mechanism is to add an asyncio Lock to the Agent instance and use it to serialize calls to invoke_async.

- In `__init__`, initialize an asyncio.Lock instance attribute, e.g., self._invoke_lock.
- In `invoke_async`, try to acquire the lock. If it is locked (meaning another invocation is running), raise a concurrency exception immediately.
- If no other invocation is running, acquire the lock, run the normal logic inside a try/finally ensuring the lock is released after the invocation finishes or errors.
- This prevents parallel invoke_async calls on the same agent instance.
- It does not affect the existing async behavior, only the concurrency.
- We need to import asyncio and define a suitable concurrency exception class (or use RuntimeError with an appropriate message). Creating a new class ConcurrencyException would be best for explicitness.

This minimally invasive patch keeps existing functionality intact but safely prevents concurrent calls.

Patch:

```python
<file>src/strands/agent/agent.py</file>
<original>     def __init__(
         self,
         model: Union[Model, str, None] = None,
         messages: Optional[Messages] = None,
         tools: Optional[list[Union[str, dict[str, str], "ToolProvider", Any]]] = None,
         system_prompt: Optional[str | list[SystemContentBlock]] = None,
         structured_output_model: Optional[Type[BaseModel]] = None,
         callback_handler: Optional[
             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
         ] = _DEFAULT_CALLBACK_HANDLER,
         conversation_manager: Optional[ConversationManager] = None,
         record_direct_tool_call: bool = True,
         load_tools_from_directory: bool = False,
         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
         *,
         agent_id: Optional[str] = None,
         name: Optional[str] = None,
         description: Optional[str] = None,
         state: Optional[Union[AgentState, dict]] = None,
         hooks: Optional[list[HookProvider]] = None,
         session_manager: Optional[SessionManager] = None,
         tool_executor: Optional[ToolExecutor] = None,
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
                 Defaults to None (no structured output).
             callback_handler: Callback for processing events as they happen during agent execution.
                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
                 If explicitly set to None, null_callback_handler is used.
             conversation_manager: Manager for conversation history and context window.
                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
             record_direct_tool_call: Whether to record direct tool calls in message history.
                 Defaults to True.
             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
                 Defaults to False.
             trace_attributes: Custom trace attributes to apply to the agent's trace span.
             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
                 Defaults to "default".
             name: name of the Agent
                 Defaults to "Strands Agents".
             description: description of what the Agent does
                 Defaults to None.
             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
                 Defaults to an empty AgentState object.
             hooks: hooks to be added to the agent hook registry
                 Defaults to None.
             session_manager: Manager for handling agent sessions including conversation history and state.
                 If provided, enables session-based persistence and state management.
             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
 
         Raises:
             ValueError: If agent id contains path separators.
         """
         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
         self.messages = messages if messages is not None else []
         # initializing self._system_prompt for backwards compatibility
         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
         self._default_structured_output_model = structured_output_model
         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
         self.name = name or _DEFAULT_AGENT_NAME
         self.description = description
 
         # If not provided, create a new PrintingCallbackHandler instance
         # If explicitly set to None, use null_callback_handler
         # Otherwise use the passed callback_handler
         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
             self.callback_handler = PrintingCallbackHandler()
         elif callback_handler is None:
             self.callback_handler = null_callback_handler
         else:
             self.callback_handler = callback_handler
 
         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
 
         # Process trace attributes to ensure they're of compatible types
         self.trace_attributes: dict[str, AttributeValue] = {}
         if trace_attributes:
             for k, v in trace_attributes.items():
                 if isinstance(v, (str, int, float, bool)) or (
                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
                 ):
                     self.trace_attributes[k] = v
 
         self.record_direct_tool_call = record_direct_tool_call
         self.load_tools_from_directory = load_tools_from_directory
 
         self.tool_registry = ToolRegistry()
 
         # Process tool list if provided
         if tools is not None:
             self.tool_registry.process_tools(tools)
 
         # Initialize tools and configuration
         self.tool_registry.initialize_tools(self.load_tools_from_directory)
         if load_tools_from_directory:
             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
 
         self.event_loop_metrics = EventLoopMetrics()
 
         # Initialize tracer instance (no-op if not configured)
         self.tracer = get_tracer()
         self.trace_span: Optional[trace_api.Span] = None
 
         # Initialize agent state management
         if state is not None:
             if isinstance(state, dict):
                 self.state = AgentState(state)
             elif isinstance(state, AgentState):
                 self.state = state
             else:
                 raise ValueError("state must be an AgentState object or a dict")
         else:
             self.state = AgentState()
 
         self.tool_caller = _ToolCaller(self)
 
         self.hooks = HookRegistry()
 
         self._interrupt_state = _InterruptState()
 
         # Initialize session management functionality
         self._session_manager = session_manager
         if self._session_manager:
             self.hooks.add_hook(self._session_manager)
 
         # Allow conversation_managers to subscribe to hooks
         self.hooks.add_hook(self.conversation_manager)
 
         self.tool_executor = tool_executor or ConcurrentToolExecutor()
 
         if hooks:
             for hook in hooks:
                 self.hooks.add_hook(hook)
         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))</original>
<patched>import asyncio

     def __init__(
         self,
         model: Union[Model, str, None] = None,
         messages: Optional[Messages] = None,
         tools: Optional[list[Union[str, dict[str, str], "ToolProvider", Any]]] = None,
         system_prompt: Optional[str | list[SystemContentBlock]] = None,
         structured_output_model: Optional[Type[BaseModel]] = None,
         callback_handler: Optional[
             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
         ] = _DEFAULT_CALLBACK_HANDLER,
         conversation_manager: Optional[ConversationManager] = None,
         record_direct_tool_call: bool = True,
         load_tools_from_directory: bool = False,
         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
         *,
         agent_id: Optional[str] = None,
         name: Optional[str] = None,
         description: Optional[str] = None,
         state: Optional[Union[AgentState, dict]] = None,
         hooks: Optional[list[HookProvider]] = None,
         session_manager: Optional[SessionManager] = None,
         tool_executor: Optional[ToolExecutor] = None,
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
                 Defaults to None (no structured output).
             callback_handler: Callback for processing events as they happen during agent execution.
                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
                 If explicitly set to None, null_callback_handler is used.
             conversation_manager: Manager for conversation history and context window.
                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
             record_direct_tool_call: Whether to record direct tool calls in message history.
                 Defaults to True.
             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
                 Defaults to False.
             trace_attributes: Custom trace attributes to apply to the agent's trace span.
             agent_id: Optional ID for the agent, useful for session management and multi-agent scenarios.
                 Defaults to "default".
             name: name of the Agent
                 Defaults to "Strands Agents".
             description: description of what the Agent does
                 Defaults to None.
             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
                 Defaults to an empty AgentState object.
             hooks: hooks to be added to the agent hook registry
                 Defaults to None.
             session_manager: Manager for handling agent sessions including conversation history and state.
                 If provided, enables session-based persistence and state management.
             tool_executor: Definition of tool execution strategy (e.g., sequential, concurrent, etc.).
 
         Raises:
             ValueError: If agent id contains path separators.
         """
         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
         self.messages = messages if messages is not None else []
         # initializing self._system_prompt for backwards compatibility
         self._system_prompt, self._system_prompt_content = self._initialize_system_prompt(system_prompt)
         self._default_structured_output_model = structured_output_model
         self.agent_id = _identifier.validate(agent_id or _DEFAULT_AGENT_ID, _identifier.Identifier.AGENT)
         self.name = name or _DEFAULT_AGENT_NAME
         self.description = description
 
         # If not provided, create a new PrintingCallbackHandler instance
         # If explicitly set to None, use null_callback_handler
         # Otherwise use the passed callback_handler
         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
             self.callback_handler = PrintingCallbackHandler()
         elif callback_handler is None:
             self.callback_handler = null_callback_handler
         else:
             self.callback_handler = callback_handler
 
         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
 
         # Process trace attributes to ensure they're of compatible types
         self.trace_attributes: dict[str, AttributeValue] = {}
         if trace_attributes:
             for k, v in trace_attributes.items():
                 if isinstance(v, (str, int, float, bool)) or (
                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
                 ):
                     self.trace_attributes[k] = v
 
         self.record_direct_tool_call = record_direct_tool_call
         self.load_tools_from_directory = load_tools_from_directory
 
         self.tool_registry = ToolRegistry()
 
         # Process tool list if provided
         if tools is not None:
             self.tool_registry.process_tools(tools)
 
         # Initialize tools and configuration
         self.tool_registry.initialize_tools(self.load_tools_from_directory)
         if load_tools_from_directory:
             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
 
         self.event_loop_metrics = EventLoopMetrics()
 
         # Initialize tracer instance (no-op if not configured)
         self.tracer = get_tracer()
         self.trace_span: Optional[trace_api.Span] = None
 
         # Initialize agent state management
         if state is not None:
             if isinstance(state, dict):
                 self.state = AgentState(state)
             elif isinstance(state, AgentState):
                 self.state = state
             else:
                 raise ValueError("state must be an AgentState object or a dict")
         else:
             self.state = AgentState()
 
         self.tool_caller = _ToolCaller(self)
 
         self.hooks = HookRegistry()
 
         self._interrupt_state = _InterruptState()
 
+        # Add asyncio lock for concurrency control
+        self._invoke_lock = asyncio.Lock()
+        
         # Initialize session management functionality
         self._session_manager = session_manager
         if self._session_manager:
             self.hooks.add_hook(self._session_manager)
 
         # Allow conversation_managers to subscribe to hooks
         self.hooks.add_hook(self.conversation_manager)
 
         self.tool_executor = tool_executor or ConcurrentToolExecutor()
 
         if hooks:
             for hook in hooks:
                 self.hooks.add_hook(hook)
         self.hooks.invoke_callbacks(AgentInitializedEvent(agent=self))
</patched>
```

```python
<file>src/strands/agent/agent.py</file>
<original>     async def invoke_async(
         self,
         prompt: AgentInput = None,
         *,
         invocation_state: dict[str, Any] | None = None,
         structured_output_model: Type[BaseModel] | None = None,
         **kwargs: Any,
     ) -> AgentResult:
         """Process a natural language prompt through the agent's event loop.
 
         This method implements the conversational interface with multiple input patterns:
         - String input: Simple text input
         - ContentBlock list: Multi-modal content blocks
         - Message list: Complete messages with roles
         - No input: Use existing conversation history
 
         Args:
             prompt: User input in various formats:
                 - str: Simple text input
                 - list[ContentBlock]: Multi-modal content blocks
                 - list[Message]: Complete messages with roles
                 - None: Use existing conversation history
             invocation_state: Additional parameters to pass through the event loop.
             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
 
         Returns:
             Result: object containing:
 
                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                 - message: The final message from the model
                 - metrics: Performance metrics from the event loop
                 - state: The final state of the event loop
         """
         events = self.stream_async(
             prompt, invocation_state=invocation_state, structured_output_model=structured_output_model, **kwargs
         )
         async for event in events:
             _ = event
 
         return cast(AgentResult, event["result"])</original>
<patched>     async def invoke_async(
         self,
         prompt: AgentInput = None,
         *,
         invocation_state: dict[str, Any] | None = None,
         structured_output_model: Type[BaseModel] | None = None,
         **kwargs: Any,
     ) -> AgentResult:
         """Process a natural language prompt through the agent's event loop.
 
         This method implements the conversational interface with multiple input patterns:
         - String input: Simple text input
         - ContentBlock list: Multi-modal content blocks
         - Message list: Complete messages with roles
         - No input: Use existing conversation history
 
         Args:
             prompt: User input in various formats:
                 - str: Simple text input
                 - list[ContentBlock]: Multi-modal content blocks
                 - list[Message]: Complete messages with roles
                 - None: Use existing conversation history
             invocation_state: Additional parameters to pass through the event loop.
             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
             **kwargs: Additional parameters to pass through the event loop.[Deprecating]
 
         Returns:
             Result: object containing:
 
                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                 - message: The final message from the model
                 - metrics: Performance metrics from the event loop
                 - state: The final state of the event loop
         """
+        if self._invoke_lock.locked():
+            raise RuntimeError("Concurrent invocations of the same Agent instance are not allowed")
+        async with self._invoke_lock:
+            events = self.stream_async(
+                prompt, invocation_state=invocation_state, structured_output_model=structured_output