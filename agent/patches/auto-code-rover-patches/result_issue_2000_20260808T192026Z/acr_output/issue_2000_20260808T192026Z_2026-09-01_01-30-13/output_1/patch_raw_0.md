The main goal is to add a new middleware hook `on_check_permission` in the Agent class to allow onion-style permission checking middleware chaining. This hook will intercept permission checks that currently are directly called by the agent's `_execute_tool_call` method by using `PermissionEngine.check_permission` directly.

The patch requires:
1. Adding a filtered list of middlewares that implement `on_check_permission` in the Agent constructor.
2. Refactoring the permission-checking section within `_execute_tool_call` to:
   - Prepare the `input_kwargs` with `tool_call` (deepcopied), resolved `tool`, and parsed `tool_input`.
   - Wrap the innermost `PermissionEngine.check_permission` as the final handler.
   - Implement the onion-style middleware chain execution for `on_check_permission`.
   - Handle the special case for already allowed tool calls (like resuming confirmed calls), allowing it to traverse the middleware chain but returning the existing ALLOW decision without re-checking the engine.
3. Maintain the existing behavior when no middleware hooked.

This change keeps all the existing logic and event handling intact, only changing the permission decision acquisition path to go through middleware for extensibility.

# modification 1: Update Agent.__init__ to filter on_check_permission middlewares
```
<file>src/agentscope/agent/_agent.py</file>
<original>        # ====================================================================
        # The Middleware-related attributes
        # ====================================================================
        # Filter middlewares by implemented hooks (only once)
        middlewares = middlewares or []
        self._reply_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_reply")
        ]
        self._reasoning_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_reasoning")
        ]
        self._acting_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_acting")
        ]
        self._model_call_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_model_call")
        ]
        self._system_prompt_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_system_prompt")
        ]
        self._compress_context_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_compress_context")
        ]</original>
<patched>        # ====================================================================
        # The Middleware-related attributes
        # ====================================================================
        # Filter middlewares by implemented hooks (only once)
        middlewares = middlewares or []
        self._reply_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_reply")
        ]
        self._reasoning_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_reasoning")
        ]
        self._acting_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_acting")
        ]
        self._model_call_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_model_call")
        ]
        self._system_prompt_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_system_prompt")
        ]
        self._compress_context_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_compress_context")
        ]
        self._check_permission_middlewares = [
            _ for _ in middlewares if _.is_implemented("on_check_permission")
        ]</patched>
```

# modification 2: Change _execute_tool_call permission check to use onion-style middleware on_check_permission
```
<file>src/agentscope/agent/_agent.py</file>
<original>        # ===================================================================
        # Step 2: Check permission by toolkit and permission engine
        # ===================================================================
        if tool_call.state == ToolCallState.ALLOWED:
            # Already allowed by user confirmation, skip permission checking
            decision = PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="Already allowed by user confirmation.",
            )
        else:
            decision = await self._engine.check_permission(
                tool,
                parsed_input,
            )</original>
<patched>        # ===================================================================
        # Step 2: Check permission by toolkit and permission engine,
        # utilizing middleware chain if present.
        # ===================================================================
        async def innermost_handler(
            *,
            tool_call: ToolCallBlock,
            tool: "Tool",
            tool_input: dict,
        ) -> PermissionDecision:
            # Innermost handler calling the built-in engine
            return await self._engine.check_permission(tool, tool_input)

        # Compose the onion-style middleware chain for permission check
        async def execute_check_permission_chain(
            index: int,
            tool_call: ToolCallBlock,
            tool: "Tool",
            tool_input: dict,
        ) -> PermissionDecision:
            if index >= len(self._check_permission_middlewares):
                return await innermost_handler(
                    tool_call=tool_call,
                    tool=tool,
                    tool_input=tool_input,
                )
            mw = self._check_permission_middlewares[index]
            input_kwargs = dict(
                tool_call=tool_call,
                tool=tool,
                tool_input=tool_input,
            )

            async def next_handler(**kwargs: dict) -> PermissionDecision:
                combined_kwargs = {**input_kwargs, **kwargs}
                return await execute_check_permission_chain(
                    index + 1,
                    combined_kwargs.get("tool_call", tool_call),
                    combined_kwargs.get("tool", tool),
                    combined_kwargs.get("tool_input", tool_input),
                )

            return await mw.on_check_permission(
                agent=self,
                input_kwargs=input_kwargs,
                next_handler=next_handler,
            )

        if tool_call.state == ToolCallState.ALLOWED:
            # Already allowed by user confirmation,
            # run middleware chain with ALLOW decision without re-checking engine
            decision = await self._run_check_permission_middleware_for_confirmed_tool_call(
                tool_call=tool_call,
                tool=tool,
                parsed_input=parsed_input,
                innermost_handler=innermost_handler,
            )
        else:
            decision = await execute_check_permission_chain(
                0,
                tool_call,
                tool,
                parsed_input,
            )
</patched>
```

# modification 3: Add new helper method _run_check_permission_middleware_for_confirmed_tool_call to run chain with ALLOW directly
```
<file>src/agentscope/agent/_agent.py</file>
<original>    async def _execute_tool_call(
        self,
        tool_call: ToolCallBlock,
        kept_rules: list[PermissionRule] | None = None,
    ) -> AsyncGenerator[
        RequireUserConfirmEvent
        | RequireExternalExecutionEvent
        | ToolResultStartEvent
        | ToolResultTextDeltaEvent
        | ToolResultDataDeltaEvent
        | ToolResultEndEvent,
        None,
    ]:
        """Execute a single tool call with permission checking and context
        management.

        This method handles the full tool call lifecycle: input validation,
        permission checking, event emission, and context writes.  The raw
        tool execution (``toolkit.call_tool``) is delegated to
        :meth:`_acting`, which is the hook point for ``on_acting``
        middleware.

        Args:
            tool_call (`ToolCallBlock`):
                The tool call block to be executed.
            kept_rules (`list[PermissionRule] | None`, defaults to `None`):
                A batch-scoped, shared accumulator of the suggested rules
                already surfaced by earlier confirmations in the same
                concurrent batch. Passed only by
                :meth:`_execute_concurrent_tool_calls`; when provided, a
                non-safety ASK whose invocation is already covered by an
                accumulated rule is de-duplicated (left ``PENDING`` and
                not surfaced again). ``None`` disables de-duplication
                (e.g. sequential execution, which already parks at the
                first ASK).

        Yields:
            `RequireUserConfirmEvent \
            | RequireExternalExecutionEvent \
            | ToolResultStartEvent \
            | ToolResultTextDeltaEvent \
            | ToolResultDataDeltaEvent \
            | ToolResultEndEvent`:
                The events generated during the tool call execution.
        """
        # ===================================================================
        # Step 1: Check and parse the tool call input:
        #  - if failed, directly return the error message to the agent
        #  - if success, continue to permission checking and tool execution
        # ===================================================================
        try:
            # Check if the tool is available
            tool = await self.toolkit.check_tool_available(
                tool_call.name,
                self.state.tool_context.activated_groups,
            )

            # Try to parse the input with the tool schema
            parsed_input = _json_loads_with_repair(
                tool_call.input,
                tool.input_schema,
            )

            # Validate the parsed input with the tool schema
            # TODO: Maybe some logic to mix the validation error in runtime
            try:
                jsonschema.validate(parsed_input, tool.input_schema)
            except jsonschema.ValidationError as e:
                raise AgentOrientedException(
                    f"Input validation failed for tool '{tool_call.name}': "
                    f"{e.message}",
                ) from e

        # The exceptions that
        #  - cannot found tool
        #  - tool not available
        #  - input parsing failure
        except AgentOrientedException as e:
            async for evt in self._handle_error_tool_call(
                tool_call,
                e.message,
                state=ToolResultState.ERROR,
            ):
                yield evt

            return
</original>
<patched>    async def _execute_tool_call(
        self,
        tool_call: ToolCallBlock,
        kept_rules: list[PermissionRule] | None = None,
    ) -> AsyncGenerator[
        RequireUserConfirmEvent
        | RequireExternalExecutionEvent
        | ToolResultStartEvent
        | ToolResultTextDeltaEvent
        | ToolResultDataDeltaEvent
        | ToolResultEndEvent,
        None,
    ]:
        """Execute a single tool call with permission checking and context
        management.

        This method handles the full tool call lifecycle: input validation,
        permission checking, event emission, and context writes.  The raw
        tool execution (``toolkit.call_tool``) is delegated to
        :meth:`_acting`, which is the hook point for ``on_acting``
        middleware.

        Args:
            tool_call (`ToolCallBlock`):
                The tool call block to be executed.
            kept_rules (`list[PermissionRule] | None`, defaults to `None`):
                A batch-scoped, shared accumulator of the suggested rules
                already surfaced by earlier confirmations in the same
                concurrent batch. Passed only by
                :meth:`_execute_concurrent_tool_calls`; when provided, a
                non-safety ASK whose invocation is already covered by an
                accumulated rule is de-duplicated (left ``PENDING`` and
                not surfaced again). ``None`` disables de-duplication
                (e.g. sequential execution, which already parks at the
                first ASK).

        Yields:
            `RequireUserConfirmEvent \
            | RequireExternalExecutionEvent \
            | ToolResultStartEvent \
            | ToolResultTextDeltaEvent \
            | ToolResultDataDeltaEvent \
            | ToolResultEndEvent`:
                The events generated during the tool call execution.
        """
        # ===================================================================
        # Step 1: Check and parse the tool call input:
        #  - if failed, directly return the error message to the agent
        #  - if success, continue to permission checking and tool execution
        # ===================================================================
        try:
            # Check if the tool is available
            tool = await self.toolkit.check_tool_available(
                tool_call.name,
                self.state.tool_context.activated_groups,
            )

            # Try to parse the input with the tool schema
            parsed_input = _json_loads_with_repair(
                tool_call.input,
                tool.input_schema,
            )

            # Validate the parsed input with the tool schema
            # TODO: Maybe some logic to mix the validation error in runtime
            try:
                jsonschema.validate(parsed_input, tool.input_schema)
            except jsonschema.ValidationError as e:
                raise AgentOrientedException(
                    f"Input validation failed for tool '{tool_call.name}': "
                    f"{e.message}",
                ) from e

        # The exceptions that
        #  - cannot found tool
        #  - tool not available
        #  - input parsing failure
        except AgentOrientedException as e:
            async for evt in self._handle_error_tool_call(
                tool_call,
                e.message,
                state=ToolResultState.ERROR,
            ):
                yield evt

            return

        # Helper: run the middleware chain for already ALLOWED tool calls on resume
    async def _run_check_permission_middleware_for_confirmed_tool_call(
        self,
        tool_call: ToolCallBlock,
        tool: "Tool",
        parsed_input: dict,
        innermost_handler: callable,
    ) -> PermissionDecision:
        """Run the on_check_permission middleware chain for tool calls
        that are already ALLOWED (confirmed) by user.

        Instead of calling the engine, immediately return an ALLOW
        decision after chaining through middleware.
        """
        async def allow_innermost_handler(
            *,
            tool_call: ToolCallBlock,
            tool: "Tool",
            tool_input: dict,
        ) -> PermissionDecision:
            return PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="Already allowed by user confirmation.",
            )

        async def execute_chain(
            index: int,
            tool_call: ToolCallBlock,
            tool: "Tool",
            tool_input: dict,
        ) -> PermissionDecision:
            if index >= len(self._check_permission_middlewares):
                return await allow_innermost_handler(
                    tool_call=tool_call,
                    tool=tool,
                    tool_input=tool_input,
                )
            mw = self._check_permission_middlewares[index]
            input_kwargs = dict(
                tool_call=tool_call,
                tool=tool,
                tool_input=tool_input,
            )

            async def next_handler(**kwargs: dict) -> PermissionDecision:
                combined_kwargs = {**input_kwargs, **kwargs}
                return await execute_chain(
                    index + 1,
                    combined_kwargs.get("tool_call", tool_call),
                    combined_kwargs.get("tool", tool),
                    combined_kwargs.get("tool_input", tool_input),
                )

            return await mw.on_check_permission(
                agent=self,
                input_kwargs=input_kwargs,
                next_handler=next_handler,
            )
</patched>
```