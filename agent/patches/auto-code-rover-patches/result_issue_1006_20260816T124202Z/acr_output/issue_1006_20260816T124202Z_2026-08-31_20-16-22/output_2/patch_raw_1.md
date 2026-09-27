Reasoning:

The key change to implement is to modify the `BeforeInvocationEvent` to accept a `messages` parameter so that hooks receive the input messages before the agent processes them. This enables early inspection or redaction of input messages.

Then, in the `Agent` class, specifically in the `stream_async` method and `structured_output_async` method, we must construct the combined input messages (from the agent's existing messages plus any prompt converted messages) early on, before invoking `BeforeInvocationEvent`. This allows hooks to see the exact messages that will be processed.

This means:

1. Update `BeforeInvocationEvent` class to include an attribute `messages` of type `Optional[Messages]` and initialize it via dataclass constructor.

2. In `stream_async`, after converting prompt to messages, build `temp_messages` by adding the prompt messages to existing messages (or handle the case if prompt is None).

3. Raise `BeforeInvocationEvent(agent=self, messages=temp_messages)` before running the agent loop, so hooks get messages early.

4. Similarly, in `structured_output_async`, move the event hook invocation to after `temp_messages` is constructed, replace the earlier call with one that includes the `messages` argument.

We keep other mechanics untouched to preserve functionality.

---

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
<patched>35 from typing import Optional
36 from ..types.content import Messages
37 from dataclasses import dataclass
38 
39 
40 @dataclass
41 class BeforeInvocationEvent(HookEvent):
42     """Event triggered at the beginning of a new agent request.
43 
44     This event is fired before the agent begins processing a new user request,
45     before any model inference or tool execution occurs. Hook providers can
46     use this event to perform request-level setup, logging, or validation.
47 
48     This event is triggered at the beginning of the following api calls:
49       - Agent.__call__
50       - Agent.stream_async
51       - Agent.structured_output
52     """
53 
54     agent: Any
55     messages: Optional[Messages] = None
</patched>
```

---

```
<file>src/strands/agent/agent.py</file>
<original>527     async def stream_async(
528         self,
529         prompt: AgentInput = None,
530         *,
531         invocation_state: dict[str, Any] | None = None,
532         structured_output_model: Type[BaseModel] | None = None,
533         **kwargs: Any,
534     ) -> AsyncIterator[Any]:
535         """Process a natural language prompt and yield events as an async iterator.
536 
537         This method provides an asynchronous interface for streaming agent events with multiple input patterns:
538         - String input: Simple text input
539         - ContentBlock list: Multi-modal content blocks
540         - Message list: Complete messages with roles
541         - No input: Use existing conversation history
542 
543         Args:
544             prompt: User input in various formats:
545                 - str: Simple text input
546                 - list[ContentBlock]: Multi-modal content blocks
547                 - list[Message]: Complete messages with roles
548                 - None: Use existing conversation history
549             invocation_state: Additional parameters to pass through the event loop.
550             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
551             **kwargs: Additional parameters to pass to the event loop.[Deprecating]
552 
553         Yields:
554             An async iterator that yields events. Each event is a dictionary containing
555                 information about the current state of processing, such as:
556 
557                 - data: Text content being generated
558                 - complete: Whether this is the final chunk
559                 - current_tool_use: Information about tools being executed
560                 - And other event data provided by the callback handler
561 
562         Raises:
563             ConcurrencyException: If another invocation is already in progress on this agent instance.
564             Exception: Any exceptions from the agent invocation will be propagated to the caller.
565 
566         Example:
567             ```python
568             async for event in agent.stream_async("Analyze this data"):
569                 if "data" in event:
570                     yield event["data"]
571             ```
572         """
573         # Acquire lock to prevent concurrent invocations
574         # Using threading.Lock instead of asyncio.Lock because run_async() creates
575         # separate event loops in different threads
576         acquired = self._invocation_lock.acquire(blocking=False)
577         if not acquired:
578             raise ConcurrencyException(
579                 "Agent is already processing a request. Concurrent invocations are not supported."
580             )
581 
582         try:
583             self._interrupt_state.resume(prompt)
584 
585             self.event_loop_metrics.reset_usage_metrics()
586 
587             merged_state = {}
588             if kwargs:
589                 warnings.warn("`**kwargs` parameter is deprecating, use `invocation_state` instead.", stacklevel=2)
590                 merged_state.update(kwargs)
591                 if invocation_state is not None:
592                     merged_state["invocation_state"] = invocation_state
593             else:
594                 if invocation_state is not None:
595                     merged_state = invocation_state
596 
597             callback_handler = self.callback_handler
598             if kwargs:
599                 callback_handler = kwargs.get("callback_handler", self.callback_handler)
600 
601             # Process input and get message to add (if any)
602             messages = await self._convert_prompt_to_messages(prompt)
603 
604             self.trace_span = self._start_agent_trace_span(messages)
605 
606             with trace_api.use_span(self.trace_span):
607                 try:
608                     events = self._run_loop(messages, merged_state, structured_output_model)
609 
610                     async for event in events:
611                         event.prepare(invocation_state=merged_state)
612 
613                         if event.is_callback_event:
614                             as_dict = event.as_dict()
615                             callback_handler(**as_dict)
616                             yield as_dict
617 
618                     result = AgentResult(*event["stop"])
619                     callback_handler(result=result)
620                     yield AgentResultEvent(result=result).as_dict()
621 
622                     self._end_agent_trace_span(response=result)
623 
624                 except Exception as e:
625                     self._end_agent_trace_span(error=e)
626                     raise
627 
628         finally:
629             self._invocation_lock.release()
630 </original>
<patched>527     async def stream_async(
528         self,
529         prompt: AgentInput = None,
530         *,
531         invocation_state: dict[str, Any] | None = None,
532         structured_output_model: Type[BaseModel] | None = None,
533         **kwargs: Any,
534     ) -> AsyncIterator[Any]:
535         """Process a natural language prompt and yield events as an async iterator.
536 
537         This method provides an asynchronous interface for streaming agent events with multiple input patterns:
538         - String input: Simple text input
539         - ContentBlock list: Multi-modal content blocks
540         - Message list: Complete messages with roles
541         - No input: Use existing conversation history
542 
543         Args:
544             prompt: User input in various formats:
545                 - str: Simple text input
546                 - list[ContentBlock]: Multi-modal content blocks
547                 - list[Message]: Complete messages with roles
548                 - None: Use existing conversation history
549             invocation_state: Additional parameters to pass through the event loop.
550             structured_output_model: Pydantic model type(s) for structured output (overrides agent default).
551             **kwargs: Additional parameters to pass to the event loop.[Deprecating]
552 
553         Yields:
554             An async iterator that yields events. Each event is a dictionary containing
555                 information about the current state of processing, such as:
556 
557                 - data: Text content being generated
558                 - complete: Whether this is the final chunk
559                 - current_tool_use: Information about tools being executed
560                 - And other event data provided by the callback handler
561 
562         Raises:
563             ConcurrencyException: If another invocation is already in progress on this agent instance.
564             Exception: Any exceptions from the agent invocation will be propagated to the caller.
565 
566         Example:
567             ```python
568             async for event in agent.stream_async("Analyze this data"):
569                 if "data" in event:
570                     yield event["data"]
571             ```
572         """
573         # Acquire lock to prevent concurrent invocations
574         # Using threading.Lock instead of asyncio.Lock because run_async() creates
575         # separate event loops in different threads
576         acquired = self._invocation_lock.acquire(blocking=False)
577         if not acquired:
578             raise ConcurrencyException(
579                 "Agent is already processing a request. Concurrent invocations are not supported."
580             )
581 
582         try:
583             self._interrupt_state.resume(prompt)
584 
585             self.event_loop_metrics.reset_usage_metrics()
586 
587             merged_state = {}
588             if kwargs:
589                 warnings.warn("`**kwargs` parameter is deprecating, use `invocation_state` instead.", stacklevel=2)
590                 merged_state.update(kwargs)
591                 if invocation_state is not None:
592                     merged_state["invocation_state"] = invocation_state
593             else:
594                 if invocation_state is not None:
595                     merged_state = invocation_state
596 
597             callback_handler = self.callback_handler
598             if kwargs:
599                 callback_handler = kwargs.get("callback_handler", self.callback_handler)
600 
601             # Process input and get message to add (if any)
602             prompt_messages = await self._convert_prompt_to_messages(prompt)
603 
604             # Compose the combined messages that will be used for the invocation
605             temp_messages: Messages = self.messages + prompt_messages
606 
607             # Fire BeforeInvocationEvent with messages
608             await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self, messages=temp_messages))
609 
610             self.trace_span = self._start_agent_trace_span(temp_messages)
611 
612             with trace_api.use_span(self.trace_span):
613                 try:
614                     events = self._run_loop(prompt_messages, merged_state, structured_output_model)
615 
616                     async for event in events:
617                         event.prepare(invocation_state=merged_state)
618 
619                         if event.is_callback_event:
620                             as_dict = event.as_dict()
621                             callback_handler(**as_dict)
622                             yield as_dict
623 
624                     result = AgentResult(*event["stop"])
625                     callback_handler(result=result)
626                     yield AgentResultEvent(result=result).as_dict()
627 
628                     self._end_agent_trace_span(response=result)
629 
630                 except Exception as e:
631                     self._end_agent_trace_span(error=e)
632                     raise
633 
634         finally:
635             self._invocation_lock.release()
630 </patched>
```

---

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
465 
466         if not self.messages and not prompt:
467             raise ValueError("No conversation history or prompt provided")
468 
469         temp_messages: Messages = self.messages + await self._convert_prompt_to_messages(prompt)
470 
471         await self.hooks.invoke_callbacks_async(BeforeInvocationEvent(agent=self, messages=temp_messages))
472 
473         with self.tracer.tracer.start_as_current_span(
474             "execute_structured_output", kind=trace_api.SpanKind.CLIENT
475         ) as structured_output_span:
476             try:
477                 structured_output_span.set_attributes(
478                     {
479                         "gen_ai.system": "strands-agents",
480                         "gen_ai.agent.name": self.name,
481                         "gen_ai.agent.id": self.agent_id,
482                         "gen_ai.operation.name": "execute_structured_output",
483                     }
484                 )
485                 if self.system_prompt:
486                     structured_output_span.add_event(
487                         "gen_ai.system.message",
488                         attributes={"role": "system", "content": serialize([{"text": self.system_prompt}])},
489                     )
490                 for message in temp_messages:
491                     structured_output_span.add_event(
492                         f"gen_ai.{message['role']}.message",
493                         attributes={"role": message["role"], "content": serialize(message["content"])},
494                     )
495                 events = self.model.structured_output(output_model, temp_messages, system_prompt=self.system_prompt)
496                 async for event in events:
497                     if isinstance(event, TypedEvent):
498                         event.prepare(invocation_state={})
499                         if event.is_callback_event:
500                             self.callback_handler(**event.as_dict())
501 
502                 structured_output_span.add_event(
503                     "gen_ai.choice", attributes={"message": serialize(event["output"].model_dump())}
504                 )
505                 return event["output"]
506 
507             finally:
508                 await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self))
507 </patched>
```

# Summary:
- Added messages field with type Optional[Messages] to BeforeInvocationEvent dataclass.
- In `stream_async`, built temp_messages by combining self.messages + prompt messages, then raised `BeforeInvocationEvent(agent=self, messages=temp_messages)`.
- In `structured_output_async`, constructed temp_messages first, then raised `BeforeInvocationEvent(agent=self, messages=temp_messages)`.
- Adjusted the imports and dataclass usage accordingly.