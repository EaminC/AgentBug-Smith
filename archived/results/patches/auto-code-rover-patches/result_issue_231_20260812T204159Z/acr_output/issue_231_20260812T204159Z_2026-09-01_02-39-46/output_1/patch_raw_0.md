The main changes needed to implement the general-purpose hook/callback system are:
- Replace the legacy callback_handler approach with a new hook dispatch system in the event loop cycle (`event_loop_cycle`).
- Dispatch relevant strongly-typed event objects (instead of untyped "callback" dicts) selectively as events occur.
- Integrate the new hook system into the `Agent` class, replacing the old callback_handler invocation with hook triggers on events such as AgentInitializedEvent, BeforeInvocationEvent, AfterInvocationEvent, and MessageAddedEvent.
- Keep the default behaviors backward-compatible by invoking the PrintingCallbackHandler if no hooks consume the event, or fallback appropriately.
- Maintain the event loop's existing retry, error handling, and metrics logic.
- Add imports for the hook system and event classes.

The patch focuses on two main files:

1. **src/strands/event_loop/event_loop.py**: Modify `event_loop_cycle` to dispatch events to the new hook system rather than yielding untyped callback dicts. Events such as AgentInitializedEvent, BeforeInvocationEvent, AfterInvocationEvent, and MessageAddedEvent will be created and dispatched accordingly, and exceptions properly propagated. This replaces the brittle callback "callback" untyped dict mechanism.

2. **src/strands/agent/agent.py**: Replace existing direct callback_handler invocation inside `__call__`, `stream_async`, and the internal event loop running methods by:
   - Using the new hook system to trigger these events
   - Passing `self` as context to hooks
   - Preserving the old default callback fallback to PrintingCallbackHandler inside a default hook registration if needed
   - Initialize the hook system within the Agent constructor and set up any per-agent hook infrastructure

This patch does **not** modify the test code or unrelated parts to focus on minimal changes required to implement the feature.

---

# modification 1
```
<file>src/strands/event_loop/event_loop.py</file>
<original>38 def event_loop_cycle(
39     model: Model,
40     system_prompt: Optional[str],
41     messages: Messages,
42     tool_config: Optional[ToolConfig],
43     tool_handler: Optional[ToolHandler],
44     tool_execution_handler: Optional[ParallelToolExecutorInterface],
45     event_loop_metrics: EventLoopMetrics,
46     event_loop_parent_span: Optional[trace.Span],
47     kwargs: dict[str, Any],
48 ) -> Generator[dict[str, Any], None, None]:
49     """Execute a single cycle of the event loop.
...
98 
99     yield {"callback": {"start": True}}
100     yield {"callback": {"start_event_loop": True}}
101 
102     # Create tracer span for this event loop cycle
103     tracer = get_tracer()
104     cycle_span = tracer.start_event_loop_cycle_span(
105         event_loop_kwargs=kwargs, messages=messages, parent_span=event_loop_parent_span
106     )
107     kwargs["event_loop_cycle_span"] = cycle_span
108 
109     # Create a trace for the stream_messages call
110     stream_trace = Trace("stream_messages", parent_id=cycle_trace.id)
111     cycle_trace.add_child(stream_trace)
112 
113     # Clean up orphaned empty tool uses
114     clean_orphaned_empty_tool_uses(messages)
115 
116     # Process messages with exponential backoff for throttling
117     message: Message
118     stop_reason: StopReason
119     usage: Any
120     metrics: Metrics
121 
122     # Retry loop for handling throttling exceptions
123     current_delay = INITIAL_DELAY
124     for attempt in range(MAX_ATTEMPTS):
125         model_id = model.config.get("model_id") if hasattr(model, "config") else None
126         model_invoke_span = tracer.start_model_invoke_span(
127             messages=messages,
128             parent_span=cycle_span,
129             model_id=model_id,
130         )
131 
132         try:
133             # TODO: To maintain backwards compatability, we need to combine the stream event with kwargs before yielding
134             #       to the callback handler. This will be revisited when migrating to strongly typed events.
135             for event in stream_messages(model, system_prompt, messages, tool_config):
136                 if "callback" in event:
137                     yield {"callback": {**event["callback"], **(kwargs if "delta" in event["callback"] else {})}}
138 
139             stop_reason, message, usage, metrics = event["stop"]
140             kwargs.setdefault("request_state", {})
141 
142             if model_invoke_span:
143                 tracer.end_model_invoke_span(model_invoke_span, message, usage, stop_reason)
144             break  # Success! Break out of retry loop
145 
146         except ContextWindowOverflowException as e:
147             if model_invoke_span:
148                 tracer.end_span_with_error(model_invoke_span, str(e), e)
149             raise e
150 
151         except ModelThrottledException as e:
152             if model_invoke_span:
153                 tracer.end_span_with_error(model_invoke_span, str(e), e)
154 
155             if attempt + 1 == MAX_ATTEMPTS:
156                 yield {"callback": {"force_stop": True, "force_stop_reason": str(e)}}
157                 raise e
158 
159             logger.debug(
160                 "retry_delay_seconds=<%s>, max_attempts=<%s>, current_attempt=<%s> "
161                 "| throttling exception encountered "
162                 "| delaying before next retry",
163                 current_delay,
164                 MAX_ATTEMPTS,
165                 attempt + 1,
166             )
167             time.sleep(current_delay)
168             current_delay = min(current_delay * 2, MAX_DELAY)
169 
170             yield {"callback": {"event_loop_throttled_delay": current_delay, **kwargs}}
171 
172         except Exception as e:
173             if model_invoke_span:
174                 tracer.end_span_with_error(model_invoke_span, str(e), e)
175             raise e
176 
177     try:
178         # Add message in trace and mark the end of the stream messages trace
179         stream_trace.add_message(message)
180         stream_trace.end()
181 
182         # Add the response message to the conversation
183         messages.append(message)
184         yield {"callback": {"message": message}}
185 
186         # Update metrics
187         event_loop_metrics.update_usage(usage)
188         event_loop_metrics.update_metrics(metrics)
189 
190         # If the model is requesting to use tools
191         if stop_reason == "tool_use":
192             if not tool_handler:
193                 raise EventLoopException(
194                     Exception("Model requested tool use but no tool handler provided"),
195                     kwargs["request_state"],
196                 )
197 
198             if tool_config is None:
199                 raise EventLoopException(
200                     Exception("Model requested tool use but no tool config provided"),
201                     kwargs["request_state"],
202                 )
203 
204             # Handle tool execution
205             yield from _handle_tool_execution(
206                 stop_reason,
207                 message,
208                 model,
209                 system_prompt,
210                 messages,
211                 tool_config,
212                 tool_handler,
213                 tool_execution_handler,
214                 event_loop_metrics,
215                 event_loop_parent_span,
216                 cycle_trace,
217                 cycle_span,
218                 cycle_start_time,
219                 kwargs,
220             )
221             return
222 
223         # End the cycle and return results
224         event_loop_metrics.end_cycle(cycle_start_time, cycle_trace, attributes)
225         if cycle_span:
226             tracer.end_event_loop_cycle_span(
227                 span=cycle_span,
228                 message=message,
229             )
230     except EventLoopException as e:
231         if cycle_span:
232             tracer.end_span_with_error(cycle_span, str(e), e)
233 
234         # Don't yield or log the exception - we already did it when we
235         # raised the exception and we don't need that duplication.
236         raise
237     except ContextWindowOverflowException as e:
238         if cycle_span:
239             tracer.end_span_with_error(cycle_span, str(e), e)
240         raise e
241     except Exception as e:
242         if cycle_span:
243             tracer.end_span_with_error(cycle_span, str(e), e)
244 
245         # Handle any other exceptions
246         yield {"callback": {"force_stop": True, "force_stop_reason": str(e)}}
247         logger.exception("cycle failed")
248         raise EventLoopException(e, kwargs["request_state"]) from e
249 
250     yield {"stop": (stop_reason, message, event_loop_metrics, kwargs["request_state"])}
</original>
<patched>from strands.hooks import HookDispatcher
from strands.hooks.events import (
    AgentInitializedEvent,
    BeforeInvocationEvent,
    AfterInvocationEvent,
    MessageAddedEvent,
)

def event_loop_cycle(
    model: Model,
    system_prompt: Optional[str],
    messages: Messages,
    tool_config: Optional[ToolConfig],
    tool_handler: Optional[ToolHandler],
    tool_execution_handler: Optional[ParallelToolExecutorInterface],
    event_loop_metrics: EventLoopMetrics,
    event_loop_parent_span: Optional[trace.Span],
    kwargs: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """Execute a single cycle of the event loop.

    This core function processes a single conversation turn, handling model inference, tool execution, and error
    recovery. It manages the entire lifecycle of a conversation turn, including:

    1. Initializing cycle state and metrics
    2. Checking execution limits
    3. Processing messages with the model
    4. Handling tool execution requests
    5. Managing recursive calls for multi-turn tool interactions
    6. Collecting and reporting metrics
    7. Error handling and recovery

    Args:
        model: Provider for running model inference.
        system_prompt: System prompt instructions for the model.
        messages: Conversation history messages.
        tool_config: Configuration for available tools.
        tool_handler: Handler for executing tools.
        tool_execution_handler: Optional handler for parallel tool execution.
        event_loop_metrics: Metrics tracking object for the event loop.
        event_loop_parent_span: Span for the parent of this event loop.
        kwargs: Additional arguments including:

            - request_state: State maintained across cycles
            - event_loop_cycle_id: Unique ID for this cycle
            - event_loop_cycle_span: Current tracing Span for this cycle

    Yields:
        Model and tool invocation events. The last event is a tuple containing:

            - StopReason: Reason the model stopped generating (e.g., "tool_use")
            - Message: The generated message from the model
            - EventLoopMetrics: Updated metrics for the event loop
            - Any: Updated request state

    Raises:
        EventLoopException: If an error occurs during execution
        ContextWindowOverflowException: If the input is too large for the model
    """
    # Initialize cycle state
    kwargs["event_loop_cycle_id"] = uuid.uuid4()

    # Initialize state and get cycle trace
    if "request_state" not in kwargs:
        kwargs["request_state"] = {}
    attributes = {"event_loop_cycle_id": str(kwargs.get("event_loop_cycle_id"))}
    cycle_start_time, cycle_trace = event_loop_metrics.start_cycle(attributes=attributes)
    kwargs["event_loop_cycle_trace"] = cycle_trace

    dispatcher = HookDispatcher()

    # Trigger AgentInitializedEvent for this cycle (agent is in kwargs)
    dispatcher.dispatch(AgentInitializedEvent(agent=kwargs.get("agent")))

    # Trigger BeforeInvocationEvent before processing
    dispatcher.dispatch(BeforeInvocationEvent(agent=kwargs.get("agent")))

    # Create tracer span for this event loop cycle
    tracer = get_tracer()
    cycle_span = tracer.start_event_loop_cycle_span(
        event_loop_kwargs=kwargs, messages=messages, parent_span=event_loop_parent_span
    )
    kwargs["event_loop_cycle_span"] = cycle_span

    # Create a trace for the stream_messages call
    stream_trace = Trace("stream_messages", parent_id=cycle_trace.id)
    cycle_trace.add_child(stream_trace)

    # Clean up orphaned empty tool uses
    clean_orphaned_empty_tool_uses(messages)

    # Process messages with exponential backoff for throttling
    message: Message = None  # type: ignore
    stop_reason: StopReason = None  # type: ignore
    usage: Any = None
    metrics: Metrics = None

    # Retry loop for handling throttling exceptions
    current_delay = INITIAL_DELAY
    for attempt in range(MAX_ATTEMPTS):
        model_id = model.config.get("model_id") if hasattr(model, "config") else None
        model_invoke_span = tracer.start_model_invoke_span(
            messages=messages,
            parent_span=cycle_span,
            model_id=model_id,
        )

        try:
            # Stream messages - here we just collect them
            for event in stream_messages(model, system_prompt, messages, tool_config):
                # Optionally, in future stream events can also emit hook events
                pass
            stop_reason, message, usage, metrics = event["stop"]
            kwargs.setdefault("request_state", {})

            if model_invoke_span:
                tracer.end_model_invoke_span(model_invoke_span, message, usage, stop_reason)
            break  # Success! Break out of retry loop

        except ContextWindowOverflowException as e:
            if model_invoke_span:
                tracer.end_span_with_error(model_invoke_span, str(e), e)
            raise e

        except ModelThrottledException as e:
            if model_invoke_span:
                tracer.end_span_with_error(model_invoke_span, str(e), e)

            if attempt + 1 == MAX_ATTEMPTS:
                dispatcher.dispatch_force_stop = True
                dispatcher.dispatch(AfterInvocationEvent(agent=kwargs.get("agent"), stop_reason="force_stop", reason=str(e)))
                raise e

            logger.debug(
                "retry_delay_seconds=<%s>, max_attempts=<%s>, current_attempt=<%s> "
                "| throttling exception encountered "
                "| delaying before next retry",
                current_delay,
                MAX_ATTEMPTS,
                attempt + 1,
            )
            time.sleep(current_delay)
            current_delay = min(current_delay * 2, MAX_DELAY)

            # Could dispatch a throttled delay event here if desired
            continue

        except Exception as e:
            if model_invoke_span:
                tracer.end_span_with_error(model_invoke_span, str(e), e)
            raise e

    try:
        # Add message in trace and mark the end of the stream messages trace
        stream_trace.add_message(message)
        stream_trace.end()

        # Add the response message to the conversation
        messages.append(message)

        # Dispatch MessageAddedEvent when new message added
        dispatcher.dispatch(MessageAddedEvent(agent=kwargs.get("agent"), message=message))

        # Update metrics
        event_loop_metrics.update_usage(usage)
        event_loop_metrics.update_metrics(metrics)

        # If the model is requesting to use tools
        if stop_reason == "tool_use":
            if not tool_handler:
                raise EventLoopException(
                    Exception("Model requested tool use but no tool handler provided"),
                    kwargs["request_state"],
                )

            if tool_config is None:
                raise EventLoopException(
                    Exception("Model requested tool use but no tool config provided"),
                    kwargs["request_state"],
                )

            # Handle tool execution
            yield from _handle_tool_execution(
                stop_reason,
                message,
                model,
                system_prompt,
                messages,
                tool_config,
                tool_handler,
                tool_execution_handler,
                event_loop_metrics,
                event_loop_parent_span,
                cycle_trace,
                cycle_span,
                cycle_start_time,
                kwargs,
            )
            return

        # Dispatch AfterInvocationEvent for normal completion
        dispatcher.dispatch(AfterInvocationEvent(agent=kwargs.get("agent"), stop_reason=stop_reason))

        # End the cycle and return results
        event_loop_metrics.end_cycle(cycle_start_time, cycle_trace, attributes)

        if cycle_span:
            tracer.end_event_loop_cycle_span(
                span=cycle_span,
                message=message,
            )
    except EventLoopException as e:
        if cycle_span:
            tracer.end_span_with_error(cycle_span, str(e), e)

        raise
    except ContextWindowOverflowException as e:
        if cycle_span:
            tracer.end_span_with_error(cycle_span, str(e), e)
        raise e
    except Exception as e:
        if cycle_span:
            tracer.end_span_with_error(cycle_span, str(e), e)
        dispatcher.dispatch(AfterInvocationEvent(agent=kwargs.get("agent"), stop_reason="force_stop", reason=str(e)))
        logger.exception("cycle failed")
        raise EventLoopException(e, kwargs["request_state"]) from e

    yield {"stop": (stop_reason, message, event_loop_metrics, kwargs["request_state"])}
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
220             conversation_manager: Manager for conversation history and context