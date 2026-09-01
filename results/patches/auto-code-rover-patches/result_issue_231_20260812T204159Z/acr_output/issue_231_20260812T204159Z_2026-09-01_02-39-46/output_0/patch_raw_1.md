Reasoning:

The issue is to implement a general-purpose hook/callback system that supports composability, selective event subscription, multiple subscribers, and typed event arguments, while preserving backward compatibility with the existing `callback_handler` system.

The current approach uses a single callback handler (a callable) that is called for all events, with no filtering or composability.

We need to:

1. Create a hook system that can manage multiple subscribers per event type.
2. Integrate this into the `Agent` class: the event loop should dispatch appropriate hook events to registered hooks, instead of just calling the single callback_handler.
3. Maintain compatibility with the existing `callback_handler` attribute, by adapting calls through the hook system.
4. The `CompositeCallbackHandler` class is similar to the new hook system, but limited to simple callable chains; we will replace this concept by a HookManager.

To keep the patch minimal:

- Add a simple `HookManager` class to `callback_handler.py` to replace `CompositeCallbackHandler`.
- In `Agent`, add `self.hooks` as a new `HookManager` instance, initialized during construction.
- If a `callback_handler` is provided, wrap it in a hook subscriber for all events (to preserve old behavior).
- Replace existing direct calls to `self.callback_handler` in agent with calls to the hook system's `emit` method.
- Adjust `_run_loop` generator to produce typed event objects and dispatch them through the hooks.
- Adjust event_loop to yield events as dicts, preferably with a type or event identifier, so the hook system can dispatch properly.
- Backward compatibility requires that if user only provided one raw callback_handler, it still receives all events.
- This patch will avoid breaking existing interface but enable subscribers to attach to specific events.

---

Patch content below.

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
<patched>from typing import Any, Callable, Dict, DefaultDict, List, Set, Type

import collections

class HookManager:
    """General purpose hook system for managing hooks and dispatching events."""

    def __init__(self) -> None:
        # Maps event class to list of subscribed handlers
        self._hooks: DefaultDict[Type, List[Callable[..., Any]]] = collections.defaultdict(list)

    def subscribe(self, event_type: Type, handler: Callable[..., Any]) -> None:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: The type of event to subscribe to.
            handler: The callable that accepts the event instance.
        """
        self._hooks[event_type].append(handler)

    def unsubscribe(self, event_type: Type, handler: Callable[..., Any]) -> None:
        """Unsubscribe a handler from a specific event type.

        Args:
            event_type: The event type to unsubscribe from.
            handler: The handler to remove.
        """
        if handler in self._hooks[event_type]:
            self._hooks[event_type].remove(handler)

    def emit(self, event: Any) -> None:
        """Emit event to all subscribed handlers of this event's type.

        Supports dispatch to base class subscribers.

        Args:
            event: The event instance to dispatch.
        """
        event_type = type(event)
        # Dispatch to all subscribers of event_type and its base classes
        called_handlers: Set[Callable[..., Any]] = set()
        for etype, handlers in self._hooks.items():
            if issubclass(event_type, etype):
                for handler in handlers:
                    if handler not in called_handlers:
                        handler(event)
                        called_handlers.add(handler)


# Keep the original CompositeCallbackHandler for backward compatibility under that name, implementing same behavior as before.
class CompositeCallbackHandler:
    """Class-based callback handler that combines multiple callback handlers.

    This handler allows multiple callback handlers to be invoked for the same events,
    enabling different processing or output formats for the same stream data.
    """

    def __init__(self, *handlers: Callable) -> None:
        """Initialize handler."""
        self.handlers = handlers

    def __call__(self, **kwargs: Any) -> None:
        """Invoke all handlers in the chain."""
        for handler in self.handlers:
            handler(**kwargs)
</patched>
```

# modification 2
```
<file>src/strands/agent/agent.py</file>
<original>179     def __init__(
180         self,
181         model: Union[Model, str, None] = None,
182         messages: Optional[Messages] = None,
183         tools: Optional[list[Union[str, dict[str, str], Any]]] = None,
184         system_prompt: Optional[str] = None,
185         callback_handler: Optional[
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
309         self.description = description
310 
311     @property
312     def tool(self) -> ToolCaller:
313         """Call tool as a function.
314 
315         Returns:
316             Tool caller through which user can invoke tool as a function.
317 
318         Example:
319             ```
320             agent = Agent(tools=[calculator])
321             agent.tool.calculator(...)
322             ```
323         """
324         return self.tool_caller
325 
326     @property
327     def tool_names(self) -> list[str]:
328         """Get a list of all registered tool names.
329 
330         Returns:
331             Names of all tools available to this agent.
332         """
333         all_tools = self.tool_registry.get_all_tools_config()
334         return list(all_tools.keys())
335 
336     @property
337     def tool_config(self) -> ToolConfig:
338         """Get the tool configuration for this agent.
339 
340         Returns:
341             The complete tool configuration.
342         """
343         return self.tool_registry.initialize_tool_config()
344 
345     def __del__(self) -> None:
346         """Clean up resources when Agent is garbage collected.
347 
348         Ensures proper shutdown of the thread pool executor if one exists.
349         """
350         if self.thread_pool_wrapper and hasattr(self.thread_pool_wrapper, "shutdown"):
351             self.thread_pool_wrapper.shutdown(wait=False)
352             logger.debug("thread pool executor shutdown complete")
353 
354     def __call__(self, prompt: str, **kwargs: Any) -> AgentResult:
355         """Process a natural language prompt through the agent's event loop.
356 
357         This method implements the conversational interface (e.g., `agent("hello!")`). It adds the user's prompt to
358         the conversation history, processes it through the model, executes any tool calls, and returns the final result.
359 
360         Args:
361             prompt: The natural language prompt from the user.
362             **kwargs: Additional parameters to pass through the event loop.
363 
364         Returns:
365             Result object containing:
366 
367                 - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
368                 - message: The final message from the model
369                 - metrics: Performance metrics from the event loop
370                 - state: The final state of the event loop
371         """
372         callback_handler = kwargs.get("callback_handler", self.callback_handler)
373 
374         self._start_agent_trace_span(prompt)
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
391             raise
</original>
<patched>179     def __init__(
180         self,
181         model: Union[Model, str, None] = None,
182         messages: Optional[Messages] = None,
183         tools: Optional[list[Union[str, dict[str, str], Any]]] = None,
184         system_prompt: Optional[str] = None,
185         callback_handler: Optional[
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
254.1     # Initialize HookManager
254.2     from strands.handlers.callback_handler import HookManager
254.3     self.hooks = HookManager()
254.4 
254.5     # For backward compatibility, subscribe given callback_handler to all events through the hook system
254.6     def _callback_handler_adapter(event: Any) -> None:
254.7         # Old callback handlers expect kwargs, so convert event's __dict__ or event to dict
254.8         # Here, we try event.__dict__ if possible, else fallback to event itself if it's dict
254.