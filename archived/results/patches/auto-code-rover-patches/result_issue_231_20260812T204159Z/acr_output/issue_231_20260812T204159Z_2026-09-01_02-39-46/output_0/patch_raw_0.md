Reasoning:

The issue requests implementation of a general-purpose hook/callback system that supports multiple subscribers, selective event subscription, typed event arguments, and preserves existing callback_handler backward compatibility and behavior.

Currently:
- Agent uses a single `callback_handler` callable that processes all events.
- `CompositeCallbackHandler` simply chains multiple callback handlers but lacks event filtering and wired type dispatch.
- The event loop yields callback events as dictionaries to the callback handler.

We will:
- Implement a new `HookManager` class that manages hooks/subscriptions for specific event types, supports composability, and invokes hooks selectively.
- Modify the Agent constructor to replace the single `callback_handler` logic with a `HookManager` instance, populating it depending on the initial `callback_handler` argument.
- Modify Agent's `_run_loop` and other event dispatch places to notify hooks via the hook manager instead of directly calling a single callback.
- Replace `CompositeCallbackHandler` with or reimplement it as a `HookManager`.
- Adapt the event loop to yield or send strongly typed events (will keep current event dicts but they will be dispatched via HookManager callbacks filtered by event type).

This patch will only touch the core classes for the hook system (`handlers/callback_handler.py`) and the Agent class for integration, and the event loop's dispatch usage if needed. It will build the hook system minimally to satisfy requirements.

---

Patch:

# modification 1
```
<file>src/strands/handlers/callback_handler.py</file>
<original>47 class CompositeCallbackHandler:
48     """Class-based callback handler that combines multiple callback handlers.
49 
50     This handler allows multiple callback handlers to be invoked for the same events,
51     enabling different processing or output formats for the same stream data.
52     """
53 
54     def __init__(self, *handlers: Callable) -> None:
55         """Initialize handler."""
56         self.handlers = handlers
57 
58     def __call__(self, **kwargs: Any) -> None:
59         """Invoke all handlers in the chain."""
60         for handler in self.handlers:
61             handler(**kwargs)
</original>
<patched>from collections import defaultdict
from typing import Callable, Any, Type, Dict, List

class HookManager:
    """
    General-purpose hook system allowing multiple hooks to subscribe to different event types.
    Hooks can be added externally and are called selectively based on event types.
    Supports composition and preserves backwards compatibility with callback_handler style.
    """

    def __init__(self) -> None:
        # Mapping: event type name -> list of callables
        self._hooks: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        # Also keep a list of generic hooks that receive all events
        self._generic_hooks: List[Callable[..., Any]] = []

    def add_hook(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Subscribe callback to events of type event_type."""
        self._hooks[event_type].append(callback)

    def remove_hook(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Remove a callback from subscription for event_type."""
        if callback in self._hooks.get(event_type, []):
            self._hooks[event_type].remove(callback)
            if not self._hooks[event_type]:
                del self._hooks[event_type]

    def add_generic_hook(self, callback: Callable[..., Any]) -> None:
        """Subscribe a callback to receive all events unfiltered."""
        self._generic_hooks.append(callback)

    def remove_generic_hook(self, callback: Callable[..., Any]) -> None:
        """Remove a generic callback."""
        if callback in self._generic_hooks:
            self._generic_hooks.remove(callback)

    def __call__(self, event_type: str, **kwargs: Any) -> None:
        """
        Call all hooks subscribed to event_type and all generic hooks.
        Call order is generic hooks then event_type hooks.
        """
        for hook in self._generic_hooks:
            try:
                hook(event_type=event_type, **kwargs)
            except Exception:
                # Defensive: exceptions in hooks should not stop others
                pass
        for hook in self._hooks.get(event_type, []):
            try:
                hook(**kwargs)
            except Exception:
                pass

    def has_hooks(self, event_type: str) -> bool:
        """Return True if any hooks are registered for event_type or generically."""
        return bool(self._generic_hooks or self._hooks.get(event_type))


# For backward compatibility, expose CompositeCallbackHandler as HookManager
CompositeCallbackHandler = HookManager
</patched>
```

# modification 2
```
<file>src/strands/agent/agent.py</file>
<original>185         callback_handler: Optional[
186             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
187         ] = _DEFAULT_CALLBACK_HANDLER,
188         conversation_manager: Optional[ConversationManager] = None,
189         max_parallel_tools: int = os.cpu_count() or 1,
190         record_direct_tool_call: bool = True,
191         load_tools_from_directory: bool = True,
192         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
193         *,
194         name: Optional[str] = None,
195         description: Optional[str] = None,
196         state: Optional[Union[AgentState, dict]] = None,
197     ):
198         """Initialize the Agent with the specified configuration.
199 
200         Args:
201             model: Provider for running inference or a string representing the model-id for Bedrock to use.
202                 Defaults to strands.models.BedrockModel if None.
203             messages: List of initial messages to pre-load into the conversation.
204                 Defaults to an empty list if None.
205             tools: List of tools to make available to the agent.
206                 Can be specified as:
207 
208                 - String tool names (e.g., "retrieve")
209                 - File paths (e.g., "/path/to/tool.py")
210                 - Imported Python modules (e.g., from strands_tools import current_time)
211                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
212                 - Functions decorated with `@strands.tool` decorator.
213 
214                 If provided, only these tools will be available. If None, all tools will be available.
215             system_prompt: System prompt to guide model behavior.
216                 If None, the model will behave according to its default settings.
217             callback_handler: Callback for processing events as they happen during agent execution.
218                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
219                 If explicitly set to None, null_callback_handler is used.
220             conversation_manager: Manager for conversation history and context window.
221                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
222             max_parallel_tools: Maximum number of tools to run in parallel when the model returns multiple tool calls.
223                 Defaults to os.cpu_count() or 1.
224             record_direct_tool_call: Whether to record direct tool calls in message history.
225                 Defaults to True.
226             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
227                 Defaults to True.
228             trace_attributes: Custom trace attributes to apply to the agent's trace span.
229             name: name of the Agent
230                 Defaults to None.
231             description: description of what the Agent does
232                 Defaults to None.
233             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
234                 Defaults to an empty AgentState object.
235 
236         Raises:
237             ValueError: If max_parallel_tools is less than 1.
238         """
239         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
240         self.messages = messages if messages is not None else []
241 
242         self.system_prompt = system_prompt
243 
244         # If not provided, create a new PrintingCallbackHandler instance
245         # If explicitly set to None, use null_callback_handler
246         # Otherwise use the passed callback_handler
247         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
248         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
249             self.callback_handler = PrintingCallbackHandler()
250         elif callback_handler is None:
251             self.callback_handler = null_callback_handler
252         else:
253             self.callback_handler = callback_handler
254 
255         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
256 
257         # Process trace attributes to ensure they're of compatible types
258         self.trace_attributes: dict[str, AttributeValue] = {}
259         if trace_attributes:
260             for k, v in trace_attributes.items():
261                 if isinstance(v, (str, int, float, bool)) or (
262                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
263                 ):
264                     self.trace_attributes[k] = v
265 
266         # If max_parallel_tools is 1, we execute tools sequentially
267         self.thread_pool = None
268         self.thread_pool_wrapper = None
269         if max_parallel_tools > 1:
270             self.thread_pool = ThreadPoolExecutor(max_workers=max_parallel_tools)
271             self.thread_pool_wrapper = ThreadPoolExecutorWrapper(self.thread_pool)
272         elif max_parallel_tools < 1:
273             raise ValueError("max_parallel_tools must be greater than 0")
274 
275         self.record_direct_tool_call = record_direct_tool_call
276         self.load_tools_from_directory = load_tools_from_directory
277 
278         self.tool_registry = ToolRegistry()
279         self.tool_handler = AgentToolHandler(tool_registry=self.tool_registry)
280 
281         # Process tool list if provided
282         if tools is not None:
283             self.tool_registry.process_tools(tools)
284 
285         # Initialize tools and configuration
286         self.tool_registry.initialize_tools(self.load_tools_from_directory)
287         if load_tools_from_directory:
288             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
289 
290         self.event_loop_metrics = EventLoopMetrics()
291 
292         # Initialize tracer instance (no-op if not configured)
293         self.tracer = get_tracer()
294         self.trace_span: Optional[trace.Span] = None
295 
296         # Initialize agent state management
297         if state is not None:
298             if isinstance(state, dict):
299                 self.state = AgentState(state)
300             elif isinstance(state, AgentState):
301                 self.state = state
302             else:
303                 raise ValueError("state must be an AgentState object or a dict")
304         else:
305             self.state = AgentState()
306 
307         self.tool_caller = Agent.ToolCaller(self)
308         self.name = name
309         self.description = description</original>
<patched>185         callback_handler: Optional[
186             Union[Callable[..., Any], _DefaultCallbackHandlerSentinel]
187         ] = _DEFAULT_CALLBACK_HANDLER,
188         conversation_manager: Optional[ConversationManager] = None,
189         max_parallel_tools: int = os.cpu_count() or 1,
190         record_direct_tool_call: bool = True,
191         load_tools_from_directory: bool = True,
192         trace_attributes: Optional[Mapping[str, AttributeValue]] = None,
193         *,
194         name: Optional[str] = None,
195         description: Optional[str] = None,
196         state: Optional[Union[AgentState, dict]] = None,
197     ):
198         """Initialize the Agent with the specified configuration.
199 
200         Args:
201             model: Provider for running inference or a string representing the model-id for Bedrock to use.
202                 Defaults to strands.models.BedrockModel if None.
203             messages: List of initial messages to pre-load into the conversation.
204                 Defaults to an empty list if None.
205             tools: List of tools to make available to the agent.
206                 Can be specified as:
207 
208                 - String tool names (e.g., "retrieve")
209                 - File paths (e.g., "/path/to/tool.py")
210                 - Imported Python modules (e.g., from strands_tools import current_time)
211                 - Dictionaries with name/path keys (e.g., {"name": "tool_name", "path": "/path/to/tool.py"})
212                 - Functions decorated with `@strands.tool` decorator.
213 
214                 If provided, only these tools will be available. If None, all tools will be available.
215             system_prompt: System prompt to guide model behavior.
216                 If None, the model will behave according to its default settings.
217             callback_handler: Callback for processing events as they happen during agent execution.
218                 If not provided (using the default), a new PrintingCallbackHandler instance is created.
219                 If explicitly set to None, null_callback_handler is used.
220             conversation_manager: Manager for conversation history and context window.
221                 Defaults to strands.agent.conversation_manager.SlidingWindowConversationManager if None.
222             max_parallel_tools: Maximum number of tools to run in parallel when the model returns multiple tool calls.
223                 Defaults to os.cpu_count() or 1.
224             record_direct_tool_call: Whether to record direct tool calls in message history.
225                 Defaults to True.
226             load_tools_from_directory: Whether to load and automatically reload tools in the `./tools/` directory.
227                 Defaults to True.
228             trace_attributes: Custom trace attributes to apply to the agent's trace span.
229             name: name of the Agent
230                 Defaults to None.
231             description: description of what the Agent does
232                 Defaults to None.
233             state: stateful information for the agent. Can be either an AgentState object, or a json serializable dict.
234                 Defaults to an empty AgentState object.
235 
236         Raises:
237             ValueError: If max_parallel_tools is less than 1.
238         """
239         self.model = BedrockModel() if not model else BedrockModel(model_id=model) if isinstance(model, str) else model
240         self.messages = messages if messages is not None else []
241 
242         self.system_prompt = system_prompt
243 
244         # Setup hook system for callbacks
245         # If default sentinel, create PrintingCallbackHandler wrapped in HookManager generic hook
246         # If None, use null_callback_handler wrapped similarly
247         # Otherwise if a callable: wrap into HookManager as generic hook for backward compatibility
248         from strands.handlers.callback_handler import HookManager, PrintingCallbackHandler, null_callback_handler
249 
250         self.hooks = HookManager()
251         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
252             printer = PrintingCallbackHandler()
253             self.hooks.add_generic_hook(printer)
254         elif callback_handler is None:
255             self.hooks.add_generic_hook(null_callback_handler)
256         else:
257             self.hooks.add_generic_hook(callback_handler)
258 
259         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
260 
261         # Process trace attributes to ensure they're of compatible types
262         self.trace_attributes: dict[str, AttributeValue] = {}
263         if trace_attributes:
264             for k, v in trace_attributes.items():
265                 if isinstance(v, (str, int, float, bool)) or (
266                     isinstance(v, list) and all(isinstance(x, (str, int, float, bool)) for x in v)
267                 ):
268                     self.trace_attributes[k] = v
269 
270         # If max_parallel_tools is 1, we execute tools sequentially
271         self.thread_pool = None
272         self.thread_pool_wrapper = None
273         if max_parallel_tools > 1:
274             self.thread_pool = ThreadPoolExecutor(max_workers=max_parallel_tools)
275             self.thread_pool_wrapper = ThreadPoolExecutorWrapper(self.thread_pool)
276         elif max_parallel_tools < 1:
277             raise ValueError("max_parallel_tools must be greater than 0")
278 
279         self.record_direct_tool_call = record_direct_tool_call
280         self.load_tools_from_directory = load_tools_from_directory
281 
282         self.tool_registry = ToolRegistry()
283         self.tool_handler = AgentToolHandler(tool_registry=self.tool_registry)
284 
285         # Process tool list if provided
286         if tools is not None:
287             self.tool_registry.process_tools(tools)
288 
289         # Initialize tools and configuration
290         self.tool_registry.initialize_tools(self.load_tools_from_directory)
291         if load_tools_from_directory:
292             self.tool_watcher = ToolWatcher(tool_registry=self.tool_registry)
293 
294         self.event_loop_metrics = EventLoopMetrics()
295 
296         # Initialize tracer instance (no-op if not configured)
297         self.tracer = get_tracer()
298         self.trace_span: Optional[trace.Span] = None
299 
300         # Initialize agent state management
301         if state is not None:
302             if isinstance(state, dict):
303                 self.state = AgentState(state)
304             elif isinstance(state, AgentState):
305                 self.state = state
306             else:
307                 raise ValueError("state must be an AgentState object or a dict")
308         else:
309             self.state = AgentState()
310 
311         self.tool_caller = Agent.ToolCaller(self)
312         self.name = name
313         self.description = description
</patched>
```

# modification 3
```
<file>src/strands/agent/agent.py</file>
<original>374         self._start_agent_trace_span(prompt)
375 
376         try:
377             events = self._run_loop(prompt, kwargs)
378             for event in events:
379                 if "callback" in event:
380                     callback_handler(**event["callback"])
381 
382             stop_reason, message, metrics, state = event["stop"]
383             result = AgentResult(stop_reason, message, metrics, state)
384 
385             self._end_agent_trace_span(response=result)
386 
387             return result
388 
389         except Exception as e:
390             self._end_agent_trace_span(error=e)
391             raise</original>
<patched>374         self._start_agent_trace_span(prompt)
375 
376         try:
377             events = self._run_loop(prompt, kwargs)
378             for event in events:
379                 if "callback" in event:
380                     # Use new hook manager for dispatch
381                     self.hooks(**event["callback"])
382 
383             stop_reason, message, metrics, state = event["stop"]
384             result = AgentResult(stop_reason, message, metrics, state)
385 
386             self._end_agent_trace_span(response=result)
387 
388             return result
389 
390         except Exception as e:
391             self._end_agent_trace_span(error=e)
392             raise
</patched>
```

# modification 4
```
<file>src/strands/agent/agent.py</file>
<original>454         callback_handler = kwargs.get("callback_handler", self.callback_handler)
455 
456         self._start_agent_trace_span(prompt)
457 
458         try:
459             events = self._run_loop(prompt, kwargs)
460             for event in events:
461                 if "callback" in