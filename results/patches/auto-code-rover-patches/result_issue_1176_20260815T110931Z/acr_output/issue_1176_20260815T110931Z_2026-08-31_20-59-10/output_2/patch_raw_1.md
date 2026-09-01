Reasoning:

The issue is that concurrent invocations to the same Agent instance corrupt the internal global state. To prevent this, we want to ensure concurrency control by disallowing concurrent invocations.

Key steps to fix the issue:

1. Add a dedicated concurrency exception class, e.g., `AgentInvocationInProgress`, to provide clear error feedback.

2. Add a concurrency control primitive: an `asyncio.Lock()` in the Agent instance initialized in the `__init__` constructor.

3. Modify the async entrypoint(s) of the agent invocation, specifically `stream_async`, to acquire this lock before processing and release it on completion or error.

4. Also modify `invoke_async` to rely on `stream_async`'s lock management external to it, so it doesn't need separate concurrency checks (this also reduces duplication).

5. Raise the concurrency exception if the lock cannot be acquired immediately (meaning an invocation is already running).

We'll thus:

- Import `asyncio` and define the exception class.

- Add `self._invocation_lock = asyncio.Lock()` in `__init__`.

- Change `stream_async` to try to acquire the lock immediately; if not possible, raise `AgentInvocationInProgress`.

- Use `async with self._invocation_lock:` to ensure serialized access.

This will make any concurrent calls raise the concurrency exception, preventing concurrent processing and related corruption.

---

Patch:

```
<file>src/strands/agent/agent.py</file>
<original>89 class Agent:
90     """Core Agent implementation.
91 
92     An agent orchestrates the following workflow:
...
105     def __init__(
106         self,
...
192         self.callback_handler: Union[Callable[..., Any], PrintingCallbackHandler]
193         if isinstance(callback_handler, _DefaultCallbackHandlerSentinel):
194             self.callback_handler = PrintingCallbackHandler()
195         elif callback_handler is None:
196             self.callback_handler = null_callback_handler
197         else:
198             self.callback_handler = callback_handler
199 
200         self.conversation_manager = conversation_manager if conversation_manager else SlidingWindowConversationManager()
...
244         self.hooks = HookRegistry()
245 
246         self._interrupt_state = _InterruptState()
...
256         self.tool_executor = tool_executor or ConcurrentToolExecutor()
...
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
...
521     async def stream_async(
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
533         - ContentBlock list: Multi-modal content blocks
534         - Message list: Complete messages with roles
535         - No input: Use existing conversation history
536 
537         Args:
538             prompt: User input in various formats:
539                 - str: Simple text input
540                 - list[ContentBlock]: Multi-modal content blocks
541                 - list[Message]: Complete messages with roles
542                 - None: Use existing conversation history
543             invocation_state: Additional parameters to pass through the event loop.
544             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
545             **kwargs: Additional parameters to pass to the event loop.[Deprecating]
546 
547         Yields:
548             An async iterator that yields events. Each event is a dictionary containing
549                 information about the current state of processing, such as:
550 
551                 - data: Text content being generated
552                 - complete: Whether this is the final chunk
553                 - current_tool_use: Information about tools being executed
554                 - And other event data provided by the callback handler
555 
556         Raises:
557             Exception: Any exceptions from the agent invocation will be propagated to the caller.
558 
559         Example:
560             ```python
561             async for event in agent.stream_async("Analyze this data"):
562                 if "data" in event:
563                     yield event["data"]
564             ```
565         """
566         self._interrupt_state.resume(prompt)
567 
568         self.event_loop_metrics.reset_usage_metrics()
569 
570         merged_state = {}
571         if kwargs:
572             warnings.warn("`**kwargs` parameter is deprecating, use `invocation_state` instead.", stacklevel=2)
573             merged_state.update(kwargs)
574             if invocation_state is not None:
575                 merged_state["invocation_state"] = invocation_state
576         else:
577             if invocation_state is not None:
578                 merged_state = invocation_state
579 
580         callback_handler = self.callback_handler
581         if kwargs:
582             callback_handler = kwargs.get("callback_handler", self.callback_handler)
583 
584         # Process input and get message to add (if any)
585         messages = await self._convert_prompt_to_messages(prompt)
586 
587         self.trace_span = self._start_agent_trace_span(messages)
588 
589         with trace_api.use_span(self.trace_span):
590             try:
591                 events = self._run_loop(messages, merged_state, structured_output_model)
592 
593                 async for event in events:
594                     event.prepare(invocation_state=merged_state)
595 
596                     if event.is_callback_event:
597                         as_dict = event.as_dict()
598                         callback_handler(**as_dict)
599                         yield as_dict
600 
601                 result = AgentResult(*event["stop"])
602                 callback_handler(result=result)
603                 yield AgentResultEvent(result=result).as_dict()
604 
605                 self._end_agent_trace_span(response=result)
606 
607             except Exception as e:
608                 self._end_agent_trace_span(error=e)
609                 raise
610 
611     async def _run_loop(
612         self,
613         messages: Messages,
614         invocation_state: dict[str, Any],
615         structured_output_model: Type[BaseModel] | None = None,
616     ) -> AsyncGenerator[TypedEvent, None]:
617         """Execute the agent's event loop with the given message and parameters.
618 
619         Args:
620             messages: The input messages to add to the conversation.
621             invocation_state: Additional parameters to pass to the event loop.
622             structured_output_model: Optional Pydantic model type for structured output.
623 
624         Yields:
625             Events from the event loop cycle.
626         """
627         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self))
628 
629         agent_result: AgentResult | None = None
630         try:
631             yield InitEventLoopEvent()
632 
633             await self._append_messages(*messages)
634 
635             structured_output_context = StructuredOutputContext(
636                 structured_output_model or self._default_structured_output_model
637             )
638 
639             # Execute the event loop cycle with retry logic for context limits
640             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
641             async for event in events:
642                 # Signal from the model provider that the message sent by the user should be redacted,
643                 # likely due to a guardrail.
644                 if (
645                     isinstance(event, ModelStreamChunkEvent)
646                     and event.chunk
647                     and event.chunk.get("redactContent")
648                     and event.chunk["redactContent"].get("redactUserContentMessage")
649                 ):
650                     self.messages[-1]["content"] = self._redact_user_content(
651                         self.messages[-1]["content"], str(event.chunk["redactContent"]["redactUserContentMessage"])
652                     )
653                     if self._session_manager:
654                         self._session_manager.redact_latest_message(self.messages[-1], self)
655                 yield event
656 
657             # Capture the result from the final event if available
658             if isinstance(event, EventLoopStopEvent):
659                 agent_result = AgentResult(*event["stop"])
660 
661         finally:
662             self.conversation_manager.apply_management(self)
663             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
664 
665     async def _execute_event_loop_cycle(
666         self, invocation_state: dict[str, Any], structured_output_context: StructuredOutputContext | None = None
667     ) -> AsyncGenerator[TypedEvent, None]:
668         """Execute the event loop cycle with retry logic for context window limits.
669 
670         This internal method handles the execution of the event loop cycle and implements
671         retry logic for handling context window overflow exceptions by reducing the
672         conversation context and retrying.
673 
674         Args:
675             invocation_state: Additional parameters to pass to the event loop.
676             structured_output_context: Optional structured output context for this invocation.
677 
678         Yields:
679             Events of the loop cycle.
680         """
681         # Add `Agent` to invocation_state to keep backwards-compatibility
682         invocation_state["agent"] = self
683 
684         if structured_output_context:
685             structured_output_context.register_tool(self.tool_registry)
686 
687         try:
688             events = event_loop_cycle(
689                 agent=self,
690                 invocation_state=invocation_state,
691                 structured_output_context=structured_output_context,
692             )
693             async for event in events:
694                 yield event
695 
696         except ContextWindowOverflowException as e:
697             # Try reducing the context size and retrying
698             self.conversation_manager.reduce_context(self, e=e)
699 
700             # Sync agent after reduce_context to keep conversation_manager_state up to date in the session
701             if self._session_manager:
702                 self._session_manager.sync_agent(self)
703 
704             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
705             async for event in events:
706                 yield event
707 
708         finally:
709             if structured_output_context:
710                 structured_output_context.cleanup(self.tool_registry)
711 
712     async def _convert_prompt_to_messages(self, prompt: AgentInput) -> Messages:
713         if self._interrupt_state.activated:
714             return []
715 
716         messages: Messages | None = None
717         if prompt is not None:
718             # Check if the latest message is toolUse
719             if len(self.messages) > 0 and any("toolUse" in content for content in self.messages[-1]["content"]):
720                 # Add toolResult message after to have a valid conversation
721                 logger.info(
722                     "Agents latest message is toolUse, appending a toolResult message to have valid conversation."
723                 )
724                 tool_use_ids = [
725                     content["toolUse"]["toolUseId"] for content in self.messages[-1]["content"] if "toolUse" in content
726                 ]
727                 await self._append_messages(
728                     {
729                         "role": "user",
730                         "content": generate_missing_tool_result_content(tool_use_ids),
731                     }
732                 )
733             if isinstance(prompt, str):
734                 # String input - convert to user message
735                 messages = [{"role": "user", "content": [{"text": prompt}]}]
736             elif isinstance(prompt, list):
737                 if len(prompt) == 0:
738                     # Empty list
739                     messages = []
740                 # Check if all item in input list are dictionaries
741                 elif all(isinstance(item, dict) for item in prompt):
742                     # Check if all items are messages
743                     if all(all(key in item for key in Message.__annotations__.keys()) for item in prompt):
744                         # Messages input - add all messages to conversation
745                         messages = cast(Messages, prompt)
746 
747                     # Check if all items are content blocks
748                     elif all(any(key in ContentBlock.__annotations__.keys() for key in item) for item in prompt):
749                         # Treat as List[ContentBlock] input - convert to user message
750                         # This allows invalid structures to be passed through to the model
751                         messages = [{"role": "user", "content": cast(list[ContentBlock], prompt)}]
752         else:
753             messages = []
754         if messages is None:
755             raise ValueError("Input prompt must be of type: `str | list[Contentblock] | Messages | None`.")
756         return messages
757 
758     def _start_agent_trace_span(self, messages: Messages) -> trace_api.Span:
759         """Starts a trace span for the agent.
760 
761         Args:
762             messages: The input messages.
763         """
764         model_id = self.model.config.get("model_id") if hasattr(self.model, "config") else None
765         return self.tracer.start_agent_span(
766             messages=messages,
767             agent_name=self.name,
768             model_id=model_id,
769             tools=self.tool_names,
770             system_prompt=self.system_prompt,
771             custom_trace_attributes=self.trace_attributes,
772             tools_config=self.tool_registry.get_all_tools_config(),
773         )
774 
775     def _end_agent_trace_span(
776         self,
777         response: Optional[AgentResult] = None,
778         error: Optional[Exception] = None,
779     ) -> None:
780         """Ends a trace span for the agent.
781 
782         Args:
783             span: The span to end.
784             response: Response to record as a trace attribute.
785             error: Error to record as a trace attribute.
786         """
787         if self.trace_span:
788             trace_attributes: dict[str, Any] = {
789                 "span": self.trace_span,
790             }
791 
792             if response:
793                 trace_attributes["response"] = response
794             if error:
795                 trace_attributes["error"] = error
796 
797             self.tracer.end_agent_span(**trace_attributes)
798 
799     def _initialize_system_prompt(
800         self, system_prompt: str | list[SystemContentBlock] | None
801     ) -> tuple[str | None, list[SystemContentBlock] | None]:
802         """Initialize system prompt fields from constructor input.
803 
804         Maintains backwards compatibility by keeping system_prompt as str when string input
805         provided, avoiding breaking existing consumers.
806 
807         Maps system_prompt input to both string and content block representations:
808         - If string: system_prompt=string, _system_prompt_content=[{text: string}]
809         - If list with text elements: system_prompt=concatenated_text, _system_prompt_content=list
810         - If list without text elements: system_prompt=None, _system_prompt_content=list
811         - If None: system_prompt=None, _system_prompt_content=None
812         """
813         if isinstance(system_prompt, str):
814             return system_prompt, [{"text": system_prompt}]
815         elif isinstance(system_prompt, list):
816             # Concatenate all text elements for backwards compatibility, None if no text found
817             text_parts = [block["text"] for block in system_prompt if "text" in block]
818             system_prompt_str = "\n".join(text_parts) if text_parts else None
819             return system_prompt_str, system_prompt
820         else:
821             return None, None
822 
823     async def _append_messages(self, *messages: Message) -> None:
824         """Appends messages to history and invoke the callbacks for the MessageAddedEvent."""
825         for message in messages:
826             self.messages.append(message)
827             await self.hooks.invoke_callbacks_async(MessageAddedEvent(agent=self, message=message))
828 
829     def _redact_user_content(self, content: list[ContentBlock], redact_message: str) -> list[ContentBlock]:
830         """Redact user content preserving toolResult blocks.
831 
832         Args:
833             content: content blocks to be redacted
834             redact_message: redact message to be replaced
835 
836         Returns:
837             Redacted content, as follows:
838             - if the message contains at least a toolResult block,
839                 all toolResult blocks(s) are kept, redacting only the result content;
840             - otherwise, the entire content of the message is replaced
841                 with a single text block with the redact message.
842         """
843         redacted_content = []
844         for block in content:
845             if "toolResult" in block:
846                 block["toolResult"]["content"] = [{"text": redact_message}]
847                 redacted_content.append(block)
848 
849         if not redacted_content:
850             # Text content is added only if no toolResult blocks were found
851             redacted_content = [{"text": redact_message}]
852 
853         return redacted_content
</original>
<patched>89 import asyncio
90 
91 class AgentInvocationInProgress(Exception):
92     """Exception raised when concurrent invocations to the same Agent instance occur."""
93     pass
94 
95 class Agent:
96     """Core Agent implementation.
97 
98     An agent orchestrates the following workflow:
...
105     def __init__(
106         self,
...
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
228         self.tracer = get_tracer