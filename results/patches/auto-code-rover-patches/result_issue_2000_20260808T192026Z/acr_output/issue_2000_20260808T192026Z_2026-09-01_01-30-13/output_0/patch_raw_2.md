```
<file>src/agentscope/agent/_agent.py</file>
<original>
    async def _execute_tool_call(
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

        # ===================================================================
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
            )

        # ===================================================================
        # Step 3: Handle the permission and execute the tool call if allowed
        # ===================================================================

        # Case 1: Ask for user confirmation if needed
        if decision.behavior in [
            PermissionBehavior.ASK,
            PermissionBehavior.PASSTHROUGH,
        ]:
            # Batch de-duplication (concurrent batches only): if an earlier
            # confirmation in this same batch already suggested an allow rule
            # that matches this invocation, do not surface a second prompt.
            # Leave the call PENDING so the next reply run re-evaluates it
            # against the engine once the user answers the first prompt (and
            # its rule has been added). Safety ASKs (bypass-immune) are never
            # de-duplicated — an allow rule cannot clear them, so each must
            # surface its own prompt.
            is_safety_ask = (
                decision.behavior == PermissionBehavior.ASK
                and decision.bypass_immune
            )
            if kept_rules is not None and not is_safety_ask:
                for rule in kept_rules:
                    if rule.tool_name != tool.name:
                        continue
                    if await _execute_async_or_sync_func(
                        tool.match_rule,
                        rule.rule_content,
                        parsed_input,
                    ):
                        # Covered by an earlier call's rule; stay PENDING and
                        # do not yield — re-evaluated on the next reply run.
                        return

            if kept_rules is not None:
                # Register this prompt's suggested rules so later calls in the
                # batch can be de-duplicated against them.
                kept_rules.extend(decision.suggested_rules or [])

            # Set the state of the tool call to "ask"
            # **Note** the update must be done before yielding the event
            self._update_tool_call_state(
                tool_call.id,
                ToolCallState.ASKING,
            )

            tool_call.suggested_rules = decision.suggested_rules or []
            yield RequireUserConfirmEvent(
                reply_id=self.state.reply_id,
                tool_calls=[tool_call],
            )
            return

        # Case 2: Denied by the permission system
        if decision.behavior == PermissionBehavior.DENY:
            async for evt in self._handle_error_tool_call(
                tool_call,
                decision.message,
                state=ToolResultState.DENIED,
            ):
                yield evt

            return

        # Case 3: Allowed by the permission system, execute the tool call and
        #  yield the events
        if decision.behavior == PermissionBehavior.ALLOW:
            self._update_tool_call_state(
                tool_call.id,
                ToolCallState.ALLOWED,
            )
            # Send start event
            yield ToolResultStartEvent(
                reply_id=self.state.reply_id,
                tool_call_id=tool_call.id,
                tool_call_name=tool_call.name,
            )
            # Send requiring external execution event if it's an external tool
            if tool.is_external_tool:
                # Update the state to "submitted" BEFORE yielding
                # because the outer loop will break immediately after
                # receiving this event, preventing any code after yield
                # from executing
                self._update_tool_call_state(
                    tool_call.id,
                    ToolCallState.SUBMITTED,
                )
                yield RequireExternalExecutionEvent(
                    reply_id=self.state.reply_id,
                    tool_calls=[tool_call],
                )
                return

            # ================================================================
            # Step 4: Delegate raw execution to _acting (middleware hook point)
            # ================================================================
            async for chunk in self._acting(tool_call):
                # The ToolResponse is the last and completed tool result here
                if isinstance(chunk, ToolResponse):
                    tool_result_block = ToolResultBlock(
                        id=tool_call.id,
                        name=tool_call.name,
                        output=[TextBlock(text=chunk.content)]
                        if isinstance(chunk.content, str)
                        else chunk.content,
                        state=chunk.state,
                        metadata=chunk.metadata,
                    )

                    # ========================================================
                    # Step 5: Truncate the tool result if exceed
                    # ========================================================
                    (
                        reserved_tool_result_block,
                        offload_tool_result_block,
                    ) = await self._split_tool_result_for_compression(
                        tool_result_block,
                    )

                    # If offload result is not empty, attach reminder to the
                    # reserved context
                    if offload_tool_result_block is not None:
                        reminder = (
                            "\n<<<TRUNCATED>>>\n<system-reminder>The "
                            "remaining content has been omitted for "
                            "limited context.{offload_reminder}"
                            "</system-reminder>"
                        )

                        offload_reminder = ""
                        if self.offloader:
                            path = await self.offloader.offload_tool_result(
                                self.state.session_id,
                                offload_tool_result_block,
                            )

                            offload_reminder = (
                                f" You can refer to the file in '{path}' "
                                f"for the truncated content if needed."
                            )

                        reminder = reminder.format(
                            offload_reminder=offload_reminder,
                        )

                        # Insert the reminder to the tool result output
                        if isinstance(reserved_tool_result_block.output, str):
                            reserved_tool_result_block.output += reminder

                        elif len(
                            reserved_tool_result_block.output,
                        ) > 0 and isinstance(
                            reserved_tool_result_block.output[-1],
                            TextBlock,
                        ):
                            reserved_tool_result_block.output[
                                -1
                            ].text += reminder

                        else:
                            reserved_tool_result_block.output += [
                                TextBlock(text=reminder),
                            ]

                    self._save_to_context([reserved_tool_result_block])
                    # Ends the tool call lifecycle.
                    self._update_tool_call_state(
                        tool_call.id,
                        ToolCallState.FINISHED,
                    )
                    # The ended event for the tool result
                    yield ToolResultEndEvent(
                        reply_id=self.state.reply_id,
                        tool_call_id=tool_call.id,
                        state=chunk.state,
                        metadata=chunk.metadata,
                    )

                else:
                    # Intermediate ToolChunk — convert to streaming events
                    async for evt in self._convert_tool_chunk_to_event(
                        tool_call.id,
                        chunk.content,
                    ):
                        yield evt

            return

        raise ValueError(
            f"Invalid permission decision behavior: {decision.behavior}",
        )
</original>
<patched>
    async def _execute_tool_call(
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

        # ===================================================================
        # Step 2: Check permission by middleware chain wrapping permission engine
        # ===================================================================
        decision: PermissionDecision

        if tool_call.state == ToolCallState.ALLOWED:
            # Already allowed by user confirmation, skip permission checking
            decision = PermissionDecision(
                behavior=PermissionBehavior.ALLOW,
                message="Already allowed by user confirmation.",
            )
        else:
            # Setup input_kwargs for middleware
            input_kwargs = {
                "tool_call": tool_call,
                "tool": tool,
                "tool_input": parsed_input,
            }

            middlewares = getattr(self, "_check_permission_middlewares", None)
            if middlewares is None:
                # Cache middleware list filtered for on_check_permission
                middlewares = [
                    mw for mw in getattr(self, "middlewares", [])
                    if mw.is_implemented("on_check_permission")
                ]
                self._check_permission_middlewares = middlewares

            # Define the innermost handler that calls the permission engine
            async def innermost_handler(
                **kwargs,
            ) -> PermissionDecision:
                # If tool_call.state is ALLOWED, returns ALLOW immediately
                # But this case is covered above, so here call underlying engine
                return await self._engine.check_permission(
                    kwargs.get("tool"),
                    kwargs.get("tool_input"),
                )

            # Build onion-style middleware invocation chain for on_check_permission
            async def call_chain(index: int, **kwargs) -> PermissionDecision:
                if index == len(middlewares):
                    return await innermost_handler(**kwargs)
                mw = middlewares[index]

                # Call the middleware on_check_permission hook
                return await mw.on_check_permission(
                    agent=self,
                    input_kwargs=kwargs,
                    next_handler=lambda **kws: call_chain(index + 1, **kws),
                )

            # Call the middleware chain
            decision = await call_chain(0, **input_kwargs)

        # ===================================================================
        # Step 3: Handle the permission and execute the tool call if allowed
        # ===================================================================

        # Case 1: Ask for user confirmation if needed
        if decision.behavior in [
            PermissionBehavior.ASK,
            PermissionBehavior.PASSTHROUGH,
        ]:
            # Batch de-duplication (concurrent batches only): if an earlier
            # confirmation in this same batch already suggested an allow rule
            # that matches this invocation, do not surface a second prompt.
            # Leave the call PENDING so the next reply run re-evaluates it
            # against the engine once the user answers the first prompt (and
            # its rule has been added). Safety ASKs (bypass-immune) are never
            # de-duplicated — an allow rule cannot clear them, so each must
            # surface its own prompt.
            is_safety_ask = (
                decision.behavior == PermissionBehavior.ASK
                and decision.bypass_immune
            )
            if kept_rules is not None and not is_safety_ask:
                for rule in kept_rules:
                    if rule.tool_name != tool.name:
                        continue
                    if await _execute_async_or_sync_func(
                        tool.match_rule,
                        rule.rule_content,
                        parsed_input,
                    ):
                        # Covered by an earlier call's rule; stay PENDING and
                        # do not yield — re-evaluated on the next reply run.
                        return

            if kept_rules is not None:
                # Register this prompt's suggested rules so later calls in the
                # batch can be de-duplicated against them.
                kept_rules.extend(decision.suggested_rules or [])

            # Set the state of the tool call to "ask"
            # **Note** the update must be done before yielding the event
            self._update_tool_call_state(
                tool_call.id,
                ToolCallState.ASKING,
            )

            tool_call.suggested_rules = decision.suggested_rules or []
            yield RequireUserConfirmEvent(
                reply_id=self.state.reply_id,
                tool_calls=[tool_call],
            )
            return

        # Case 2: Denied by the permission system
        if decision.behavior == PermissionBehavior.DENY:
            async for evt in self._handle_error_tool_call(
                tool_call,
                decision.message,
                state=ToolResultState.DENIED,
            ):
                yield evt

            return

        # Case 3: Allowed by the permission system, execute the tool call and
        #  yield the events
        if decision.behavior == PermissionBehavior.ALLOW:
            self._update_tool_call_state(
                tool_call.id,
                ToolCallState.ALLOWED,
            )
            # Send start event
            yield ToolResultStartEvent(
                reply_id=self.state.reply_id,
                tool_call_id=tool_call.id,
                tool_call_name=tool_call.name,
            )
            # Send requiring external execution event if it's an external tool
            if tool.is_external_tool:
                # Update the state to "submitted" BEFORE yielding
                # because the outer loop will break immediately after
                # receiving this event, preventing any code after yield
                # from executing
                self._update_tool_call_state(
                    tool_call.id,
                    ToolCallState.SUBMITTED,
                )
                yield RequireExternalExecutionEvent(
                    reply_id=self.state.reply_id,
                    tool_calls=[tool_call],
                )
                return

            # ================================================================
            # Step 4: Delegate raw execution to _acting (middleware hook point)
            # ================================================================
            async for chunk in self._acting(tool_call):
                # The ToolResponse is the last and completed tool result here
                if isinstance(chunk, ToolResponse):
                    tool_result_block = ToolResultBlock(
                        id=tool_call.id,
                        name=tool_call.name,
                        output=[TextBlock(text=chunk.content)]
                        if isinstance(chunk.content, str)
                        else chunk.content,
                        state=chunk.state,
                        metadata=chunk.metadata,
                    )

                    # ========================================================
                    # Step 5: Truncate the tool result if exceed
                    # ========================================================
                    (
                        reserved_tool_result_block,
                        offload_tool_result_block,
                    ) = await self._split_tool_result_for_compression(
                        tool_result_block,
                    )

                    # If offload result is not empty, attach reminder to the
                    # reserved context
                    if offload_tool_result_block