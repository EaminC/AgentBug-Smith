```
<file>src/strands/agent/agent.py</file>
<original>
656         finally:
657             self.conversation_manager.apply_management(self)
658             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
</original>
<patched>
656         finally:
657             # Apply conversation management BEFORE invoking AfterInvocationEvent hooks to reduce messages
658             # Additionally, allow apply_management calls inside AfterInvocationEvent hook callbacks to be effective.
659             self.conversation_manager.apply_management(self)
660             await self.hooks.invoke_callbacks_async(AfterInvocationEvent(agent=self, result=agent_result))
</patched>
```

```
<file>src/strands/agent/conversation_manager/sliding_window_conversation_manager.py</file>
<original>
35     def apply_management(self, agent: "Agent", **kwargs: Any) -> None:
36         """Apply the sliding window to the agent's messages array to maintain a manageable history size.
37 
38         This method is called after every event loop cycle to apply a sliding window if the message count
39         exceeds the window size.
40 
41         Args:
42             agent: The agent whose messages will be managed.
43                 This list is modified in-place.
44             **kwargs: Additional keyword arguments for future extensibility.
45         """
46         messages = agent.messages
47 
48         if len(messages) <= self.window_size:
49             logger.debug(
50                 "message_count=<%s>, window_size=<%s> | skipping context reduction", len(messages), self.window_size
51             )
52             return
53         self.reduce_context(agent)
</original>
<patched>
35     def apply_management(self, agent: "Agent", **kwargs: Any) -> None:
36         """Apply the sliding window to the agent's messages array to maintain a manageable history size.
37 
38         This method is called after every event loop cycle or can be called dynamically during loop iterations.
39         It applies a sliding window if the message count exceeds the window size.
40 
41         Args:
42             agent: The agent whose messages will be managed.
43                 This list is modified in-place.
44             **kwargs: Additional keyword arguments for future extensibility.
45         """
46         messages = agent.messages
47 
48         if len(messages) <= self.window_size:
49             logger.debug(
50                 "message_count=<%s>, window_size=<%s> | skipping context reduction", len(messages), self.window_size
51             )
52             return
53         self.reduce_context(agent)
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>
660     async def _execute_event_loop_cycle(
661         self, invocation_state: dict[str, Any], structured_output_context: StructuredOutputContext | None = None
662     ) -> AsyncGenerator[TypedEvent, None]:
663         """Execute the event loop cycle with retry logic for context window limits.
664 
665         This internal method handles the execution of the event loop cycle and implements
666         retry logic for handling context window overflow exceptions by reducing the
667         conversation context and retrying.
668 
669         Args:
670             invocation_state: Additional parameters to pass to the event loop.
671             structured_output_context: Optional structured output context for this invocation.
672 
673         Yields:
674             Events of the loop cycle.
675         """
676         # Add `Agent` to invocation_state to keep backwards-compatibility
677         invocation_state["agent"] = self
678 
679         if structured_output_context:
680             structured_output_context.register_tool(self.tool_registry)
681 
682         try:
683             events = event_loop_cycle(
684                 agent=self,
685                 invocation_state=invocation_state,
686                 structured_output_context=structured_output_context,
687             )
688             async for event in events:
689                 yield event
690 
691         except ContextWindowOverflowException as e:
692             # Try reducing the context size and retrying
693             self.conversation_manager.reduce_context(self, e=e)
694 
695             # Sync agent after reduce_context to keep conversation_manager_state up to date in the session
696             if self._session_manager:
697                 self._session_manager.sync_agent(self)
698 
699             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
</original>
<patched>
660     async def _execute_event_loop_cycle(
661         self, invocation_state: dict[str, Any], structured_output_context: StructuredOutputContext | None = None
662     ) -> AsyncGenerator[TypedEvent, None]:
663         """Execute the event loop cycle with retry logic for context window limits.
664 
665         This internal method handles the execution of the event loop cycle and implements
666         retry logic for handling context window overflow exceptions by reducing the
667         conversation context and retrying.
668 
669         Args:
670             invocation_state: Additional parameters to pass to the event loop.
671             structured_output_context: Optional structured output context for this invocation.
672 
673         Yields:
674             Events of the loop cycle.
675         """
676         # Add `Agent` to invocation_state to keep backwards-compatibility
677         invocation_state["agent"] = self
678 
679         if structured_output_context:
680             structured_output_context.register_tool(self.tool_registry)
681 
682         try:
683             events = event_loop_cycle(
684                 agent=self,
685                 invocation_state=invocation_state,
686                 structured_output_context=structured_output_context,
687             )
688             async for event in events:
689                 # Apply conversation management during loop iteration to reduce message count progressively
690                 self.conversation_manager.apply_management(self)
691                 yield event
692 
693         except ContextWindowOverflowException as e:
694             # Try reducing the context size and retrying
695             self.conversation_manager.reduce_context(self, e=e)
696 
697             # Sync agent after reduce_context to keep conversation_manager_state up to date in the session
698             if self._session_manager:
699                 self._session_manager.sync_agent(self)
700 
701             events = self._execute_event_loop_cycle(invocation_state, structured_output_context)
</patched>
```