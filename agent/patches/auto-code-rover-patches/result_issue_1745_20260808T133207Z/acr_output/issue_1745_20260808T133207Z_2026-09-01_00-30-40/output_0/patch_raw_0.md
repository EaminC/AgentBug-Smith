```
<file>src/agentscope/agent/_agent.py</file>
<original>    async def reply_stream(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Reply to the given inputs and stream agent events.

        Args:
            inputs (`Msg | list[Msg] | UserConfirmResultEvent | \
            UserInterruptEvent | ExternalExecutionResultEvent | None`, \
            optional):
                The inputs that trigger this reply. See :meth:`reply` for
                the full list of accepted variants.

        Yields:
            `AgentEvent`:
                Streamed events produced during the reply.

        .. note:: If requiring outside interaction for multiple tool calls
            and only receive partial confirmation or execution results, the
            agent won't re-send the requiring events for the unconfirmed
            or unexecuted tool calls.
        """
        async for chunk in self._reply(inputs=inputs):
            if not isinstance(chunk, Msg):
                yield chunk
</original>
<patched>    async def reply_stream(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
        output_schema: dict | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Reply to the given inputs and stream agent events.

        Args:
            inputs (`Msg | list[Msg] | UserConfirmResultEvent | \
            UserInterruptEvent | ExternalExecutionResultEvent | None`, \
            optional):
                The inputs that trigger this reply. See :meth:`reply` for
                the full list of accepted variants.
            output_schema (`dict | None`, optional):
                Optional JSON schema defining the structured output format 
                expected from the agent.

        Yields:
            `AgentEvent`:
                Streamed events produced during the reply.

        .. note:: If requiring outside interaction for multiple tool calls
            and only receive partial confirmation or execution results, the
            agent won't re-send the requiring events for the unconfirmed
            or unexecuted tool calls.
        """
        async for chunk in self._reply(inputs=inputs, output_schema=output_schema):
            if not isinstance(chunk, Msg):
                yield chunk
</patched>
```

```
<file>src/agentscope/agent/_agent.py</file>
<original>    async def reply(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
    ) -> Msg:
        """Reply to the given inputs, consuming all streamed events.

        Args:
            inputs (`Msg | list[Msg] | UserConfirmResultEvent | \
            UserInterruptEvent | ExternalExecutionResultEvent | None`, \
            optional):
                The inputs that trigger this reply. It can be:

                - a single `Msg` or a list of `Msg` objects to start a new
                  reply,
                - a `UserConfirmResultEvent` or
                  `ExternalExecutionResultEvent` to continue from the
                  outside interaction required by the previous reply,
                - a `UserInterruptEvent` to abort a parked reply — the
                  agent closes all pending tool calls with an interrupted
                  tool result and ends the reply without entering the
                  reasoning-acting loop,
                - `None` if there is nothing new to feed in (e.g. just
                  continue from the current state).

        Returns:
            `Msg`:
                A final reply message.
        """
        final_msg: Msg | None = None
        async for evt_or_msg in self._reply(inputs=inputs):
            if isinstance(evt_or_msg, Msg):
                final_msg = evt_or_msg
        if final_msg is None:
            raise RuntimeError("Agent did not produce a final message.")
        return final_msg
</original>
<patched>    async def reply(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
        output_schema: dict | None = None,
    ) -> Msg:
        """Reply to the given inputs, consuming all streamed events.

        Args:
            inputs (`Msg | list[Msg] | UserConfirmResultEvent | \
            UserInterruptEvent | ExternalExecutionResultEvent | None`, \
            optional):
                The inputs that trigger this reply. It can be:

                - a single `Msg` or a list of `Msg` objects to start a new
                  reply,
                - a `UserConfirmResultEvent` or
                  `ExternalExecutionResultEvent` to continue from the
                  outside interaction required by the previous reply,
                - a `UserInterruptEvent` to abort a parked reply — the
                  agent closes all pending tool calls with an interrupted
                  tool result and ends the reply without entering the
                  reasoning-acting loop,
                - `None` if there is nothing new to feed in (e.g. just
                  continue from the current state).
            output_schema (`dict | None`, optional):
                Optional JSON schema defining the structured output format 
                expected from the agent.

        Returns:
            `Msg`:
                A final reply message.
        """
        final_msg: Msg | None = None
        async for evt_or_msg in self._reply(inputs=inputs, output_schema=output_schema):
            if isinstance(evt_or_msg, Msg):
                final_msg = evt_or_msg
        if final_msg is None:
            raise RuntimeError("Agent did not produce a final message.")
        return final_msg
</patched>
```

```
<file>src/agentscope/agent/_agent.py</file>
<original>    async def _reply(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        # existing implementation...
        ...
</original>
<patched>    async def _reply(
        self,
        inputs: Msg
        | list[Msg]
        | UserConfirmResultEvent
        | UserInterruptEvent
        | ExternalExecutionResultEvent
        | None = None,
        output_schema: dict | None = None,
    ) -> AsyncGenerator[AgentEvent | Msg, None]:
        """Internal reply method that supports streaming and structured output."""
        # Attach output_schema to instance or pass down as needed:
        self._current_output_schema = output_schema

        # existing implementation logic below...
        # [Existing logic remains unchanged, but where messages are constructed or emitted,
        # if output_schema is set, transform or validate the structured output accordingly.]
        ...

        # Clean up output_schema after reply done
        self._current_output_schema = None
</patched>
```