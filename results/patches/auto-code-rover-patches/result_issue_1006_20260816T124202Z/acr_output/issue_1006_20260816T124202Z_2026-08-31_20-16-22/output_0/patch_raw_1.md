The main goal is to expose the input messages to the existing BeforeInvocationEvent hook, so that hooks listening to this event can inspect or modify the messages before the agent processes them (and before they are added to memory). This requires:

1. Modifying the `BeforeInvocationEvent` class to accept an optional `messages` parameter, preserving backward compatibility with existing usage.

2. Modifying the invocation of this event in `_run_loop` so that it passes the actual input `messages` argument.

3. Modifying the `structured_output_async` method to generate the combined `temp_messages` first (combining history and prompt), validate input, then invoke the `BeforeInvocationEvent` hook passing these temp_messages so that guardrail hooks can intervene at this earliest stage.

This achieves a consistent behavior where `BeforeInvocationEvent` hooks have access to the actual input messages, even before messages are appended to the agent memory.

---

# modification 1
Extend `BeforeInvocationEvent` to accept an optional `messages` parameter.

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
48     def __init__(self, agent: "Agent", messages: list["Message"] | None = None) -> None:
49         super().__init__(agent=agent)
50         self.messages = messages
</patched>
```

---

# modification 2
Modify `Agent._run_loop` to pass `messages` to the `BeforeInvocationEvent` hook.

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
</original>
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
</patched>
```

---

# modification 3
Modify `structured_output_async` method to move the event invocation to after `temp_messages` is constructed and validated, passing `temp_messages` to the event.

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
</original>
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
</patched>
```