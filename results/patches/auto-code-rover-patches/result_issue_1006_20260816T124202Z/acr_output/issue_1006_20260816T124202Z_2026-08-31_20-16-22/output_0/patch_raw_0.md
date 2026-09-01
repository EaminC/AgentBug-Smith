Reasoning:
The issue requires exposing the messages that are being used as input to the `BeforeInvocationEvent` hook. Currently, this event is invoked without knowledge of those messages, which limits the ability for guardrails or redaction before the agent processes the messages or adds them to memory.

To solve this:
1. Modify the `BeforeInvocationEvent` class to accept an optional `messages` parameter and store it.
2. Change the invocations of `BeforeInvocationEvent` (notably in `_run_loop` and in `structured_output_async`) to pass the input messages (or temp_messages for `structured_output_async`) as the new messages argument, so hooks can inspect/modify them.
3. Ensure the invocation in `_run_loop` uses the `messages` argument that `_run_loop` receives; this gives message visibility to hooks early in the invocation.
4. For `structured_output_async` method, reorder the input validation and construction of `temp_messages` to before invocation of the `BeforeInvocationEvent` hook and then invoke the hook with the constructed `temp_messages`. This allows redaction/editing before the invocation continues.

These are minimal changes that preserve existing functionality but provide new hooks access to input messages.

Patch:


```
<file>src/strands/hooks/events.py</file>
<original>35 class BeforeInvocationEvent(HookEvent):
36     """Event triggered at the beginning of a new agent request.
37 
38     This event is fired before the agent begins processing a new user request,
39     before any model inference or tool execution occurs. Hook providers can
40     use this event to perform request-level setup, logging, or validation.
41 
42     This event is triggered at the beginning of the following api calls:
43       - Agent.__call__
44       - Agent.stream_async
45       - Agent.structured_output
46     """
47 
48     pass
</original>
<patched>35 class BeforeInvocationEvent(HookEvent):
36     """Event triggered at the beginning of a new agent request.
37 
38     This event is fired before the agent begins processing a new user request,
39     before any model inference or tool execution occurs. Hook providers can
40     use this event to perform request-level setup, logging, or validation.
41 
42     This event is triggered at the beginning of the following api calls:
43       - Agent.__call__
44       - Agent.stream_async
45       - Agent.structured_output
46     """
47 
48     def __init__(self, *, agent: "Agent", messages: Optional[Messages] = None) -> None:
49         super().__init__(agent=agent)
50         self.messages = messages
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>437     async def structured_output_async(self, output_model: Type[T], prompt: AgentInput = None) -> T:
438         """This method allows you to get structured output from the agent.
439 
440         If you pass in a prompt, it will be used temporarily without adding it to the conversation history.
441         If you don't pass in a prompt, it will use only the existing conversation history to respond.
442 
443         For smaller models, you may want to use the optional prompt to add additional instructions to explicitly
444         instruct the model to output the structured data.
445 
446         Args:
447             output_model: The output model (a JSON schema written as a Pydantic BaseModel)
448                 that the agent will use when responding.
449             prompt: The prompt to use for the agent (will not be added to conversation history).
450 
451         Raises:
452             ValueError: If no conversation history or prompt is provided.
453         -
454         """
455         if self._interrupt_state.activated:
456             raise RuntimeError("cannot call structured output during interrupt")
457 
458         warnings.warn(
459             "Agent.structured_output_async method is deprecated."
460             " You should pass in `structured_output_model` directly into the agent invocation."
461             " see: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/structured-output/",
462             category=DeprecationWarning,
463             stacklevel=2,
464         )
465         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self))
466         with self.tracer.tracer.start_as_current_span(
467             "execute_structured_output", kind=trace_api.SpanKind.CLIENT
468         ) as structured_output_span:
469             try:
470                 if not self.messages and not prompt:
471                     raise ValueError("No conversation history or prompt provided")
472 
473                 temp_messages: Messages = self.messages + await self._convert_prompt_to_messages(prompt)
474 
475                 structured_output_span.set_attributes(
476                     {
477                         "gen_ai.system": "strands-agents",
478                         "gen_ai.agent.name": self.name,
479                         "gen_ai.agent.id": self.agent_id,
480                         "gen_ai.operation.name": "execute_structured_output",
481                     }
482                 )
483                 if self.system_prompt:
484                     structured_output_span.add_event(
485                         "gen_ai.system.message",
486                         attributes={"role": "system", "content": serialize([{"text": self.system_prompt}])},
487                     )
488                 for message in temp_messages:
489                     structured_output_span.add_event(
490                         f"gen_ai.{message['role']}.message",
491                         attributes={"role": message["role"], "content": serialize(message["content"])},
492                     )
493                 events = self.model.structured_output(output_model, temp_messages, system_prompt=self.system_prompt)
494                 async for event in events:
495                     if isinstance(event, TypedEvent):
496                         event.prepare(invocation_state={})
497                         if event.is_callback_event:
498                             self.callback_handler(**event.as_dict())
499 
500                 structured_output_span.add_event(
501                     "gen_ai.choice", attributes={"message": serialize(event["output"].model_dump())}
502                 )
503                 return event["output"]
504 
505             finally:
506                 await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self))
507 </original>
<patched>437     async def structured_output_async(self, output_model: Type[T], prompt: AgentInput = None) -> T:
438         """This method allows you to get structured output from the agent.
439 
440         If you pass in a prompt, it will be used temporarily without adding it to the conversation history.
441         If you don't pass in a prompt, it will use only the existing conversation history to respond.
442 
443         For smaller models, you may want to use the optional prompt to add additional instructions to explicitly
444         instruct the model to output the structured data.
445 
446         Args:
447             output_model: The output model (a JSON schema written as a Pydantic BaseModel)
448                 that the agent will use when responding.
449             prompt: The prompt to use for the agent (will not be added to conversation history).
450 
451         Raises:
452             ValueError: If no conversation history or prompt is provided.
453         -
454         """
455         if self._interrupt_state.activated:
456             raise RuntimeError("cannot call structured output during interrupt")
457 
458         warnings.warn(
459             "Agent.structured_output_async method is deprecated."
460             " You should pass in `structured_output_model` directly into the agent invocation."
461             " see: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/agents/structured-output/",
462             category=DeprecationWarning,
463             stacklevel=2,
464         )
465         if not self.messages and not prompt:
466             raise ValueError("No conversation history or prompt provided")
467 
468         temp_messages: Messages = self.messages + await self._convert_prompt_to_messages(prompt)
469 
470         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self, messages=temp_messages))
471 
472         with self.tracer.tracer.start_as_current_span(
473             "execute_structured_output", kind=trace_api.SpanKind.CLIENT
474         ) as structured_output_span:
475             try:
476                 structured_output_span.set_attributes(
477                     {
478                         "gen_ai.system": "strands-agents",
479                         "gen_ai.agent.name": self.name,
480                         "gen_ai.agent.id": self.agent_id,
481                         "gen_ai.operation.name": "execute_structured_output",
482                     }
483                 )
484                 if self.system_prompt:
485                     structured_output_span.add_event(
486                         "gen_ai.system.message",
487                         attributes={"role": "system", "content": serialize([{"text": self.system_prompt}])},
488                     )
489                 for message in temp_messages:
490                     structured_output_span.add_event(
491                         f"gen_ai.{message['role']}.message",
492                         attributes={"role": message["role"], "content": serialize(message["content"])},
493                     )
494                 events = self.model.structured_output(output_model, temp_messages, system_prompt=self.system_prompt)
495                 async for event in events:
496                     if isinstance(event, TypedEvent):
497                         event.prepare(invocation_state={})
498                         if event.is_callback_event:
499                             self.callback_handler(**event.as_dict())
500 
501                 structured_output_span.add_event(
502                     "gen_ai.choice", attributes={"message": serialize(event["output"].model_dump())}
503                 )
504                 return event["output"]
505 
506             finally:
507                 await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self))
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>631     async def _run_loop(
632         self,
633         messages: Messages,
634         invocation_state: dict[str, Any],
635         structured_output_model: Type[BaseModel] | None = None,
636     ) -> AsyncGenerator[TypedEvent, None]:
637         """Execute the agent's event loop with the given message and parameters.
638 
639         Args:
640             messages: The input messages to add to the conversation.
641             invocation_state: Additional parameters to pass to the event loop.
642             structured_output_model: Optional Pydantic model type for structured output.
643 
644         Yields:
645             Events from the event loop cycle.
646         """
647         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self))
648 
649         agent_result: AgentResult | None = None
650         try:
651             yield InitEventLoopEvent()
652 
653             await self._append_messages(*messages)
654 
655             structured_output_context = StructuredOutputContext(
656                 structured_output_model or self._default_structured_output_model
657             )
658 
659             # Execute the event loop cycle with retry logic for context limits
660             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
661             async for event in events:
662                 # Signal from the model provider that the message sent by the user should be redacted,
663                 # likely due to a guardrail.
664                 if (
665                     isinstance(event, ModelStreamChunkEvent)
666                     and event.chunk
667                     and event.chunk.get("redactContent")
668                     and event.chunk["redactContent"].get("redactUserContentMessage")
669                 ):
670                     self.messages[-1]["content"] = self._redact_user_content(
671                         self.messages[-1]["content"], str(event.chunk["redactContent"]["redactUserContentMessage"])
672                     )
673                     if self._session_manager:
674                         self._session_manager.redact_latest_message(self.messages[-1], self)
675                 yield event
676 
677             # Capture the result from the final event if available
678             if isinstance(event, EventLoopStopEvent):
679                 agent_result = AgentResult(*event["stop"])
680 
681         finally:
682             self.conversation_manager.apply_management(self)
683             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
684 </original>
<patched>631     async def _run_loop(
632         self,
633         messages: Messages,
634         invocation_state: dict[str, Any],
635         structured_output_model: Type[BaseModel] | None = None,
636     ) -> AsyncGenerator[TypedEvent, None]:
637         """Execute the agent's event loop with the given message and parameters.
638 
639         Args:
640             messages: The input messages to add to the conversation.
641             invocation_state: Additional parameters to pass to the event loop.
642             structured_output_model: Optional Pydantic model type for structured output.
643 
644         Yields:
645             Events from the event loop cycle.
646         """
647         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self, messages=messages))
648 
649         agent_result: AgentResult | None = None
650         try:
651             yield InitEventLoopEvent()
652 
653             await self._append_messages(*messages)
654 
655             structured_output_context = StructuredOutputContext(
656                 structured_output_model or self._default_structured_output_model
657             )
658 
659             # Execute the event loop cycle with retry logic for context limits
660             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
661             async for event in events:
662                 # Signal from the model provider that the message sent by the user should be redacted,
663                 # likely due to a guardrail.
664                 if (
665                     isinstance(event, ModelStreamChunkEvent)
666                     and event.chunk
667                     and event.chunk.get("redactContent")
668                     and event.chunk["redactContent"].get("redactUserContentMessage")
669                 ):
670                     self.messages[-1]["content"] = self._redact_user_content(
671                         self.messages[-1]["content"], str(event.chunk["redactContent"]["redactUserContentMessage"])
672                     )
673                     if self._session_manager:
674                         self._session_manager.redact_latest_message(self.messages[-1], self)
675                 yield event
676 
677             # Capture the result from the final event if available
678             if isinstance(event, EventLoopStopEvent):
679                 agent_result = AgentResult(*event["stop"])
680 
681         finally:
682             self.conversation_manager.apply_management(self)
683             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
684 </patched>
```