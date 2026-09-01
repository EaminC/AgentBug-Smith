```
<file>src/strands/agent/agent.py</file>
<original>        try:
            self._interrupt_state.resume(prompt)

            self.event_loop_metrics.reset_usage_metrics()

            merged_state = {}
            if kwargs:
                warnings.warn("`**kwargs` parameter is deprecating, use `invocation_state` instead.", stacklevel=2)
                merged_state.update(kwargs)
                if invocation_state is not None:
                    merged_state["invocation_state"] = invocation_state
            else:
                if invocation_state is not None:
                    merged_state = invocation_state

            callback_handler = self.callback_handler
            if kwargs:
                callback_handler = kwargs.get("callback_handler", self.callback_handler)

            # Process input and get message to add (if any)
            messages = await self._convert_prompt_to_messages(prompt)

            self.trace_span = self._start_agent_trace_span(messages)

            with trace_api.use_span(self.trace_span):
                try:
                    events = self._run_loop(messages, merged_state, structured_output_model, structured_output_prompt)

                    async for event in events:
                        event.prepare(invocation_state=merged_state)

                        if event.is_callback_event:
                            as_dict = event.as_dict()
                            callback_handler(**as_dict)
                            yield as_dict

                    result = AgentResult(*event["stop"])
                    callback_handler(result=result)
                    yield AgentResultEvent(result=result).as_dict()

                    self._end_agent_trace_span(response=result)

                except Exception as e:
                    self._end_agent_trace_span(error=e)
                    raise

        finally:
            # Clear cancel signal to allow agent reuse after cancellation
</original>
<patched>        try:
            self._interrupt_state.resume(prompt)

            self.event_loop_metrics.reset_usage_metrics()

            merged_state = {}
            if kwargs:
                warnings.warn("`**kwargs` parameter is deprecating, use `invocation_state` instead.", stacklevel=2)
                merged_state.update(kwargs)
                if invocation_state is not None:
                    merged_state["invocation_state"] = invocation_state
            else:
                if invocation_state is not None:
                    merged_state = invocation_state

            callback_handler = self.callback_handler
            if kwargs:
                callback_handler = kwargs.get("callback_handler", self.callback_handler)

            # Process input and get message to add (if any)
            messages = await self._convert_prompt_to_messages(prompt)

            # Compute token size of current agent context messages and store in event_loop_metrics
            context_token_size = self._compute_messages_token_size(messages)
            self.event_loop_metrics.current_agent_context_tokens = context_token_size

            self.trace_span = self._start_agent_trace_span(messages)

            with trace_api.use_span(self.trace_span):
                try:
                    events = self._run_loop(messages, merged_state, structured_output_model, structured_output_prompt)

                    async for event in events:
                        event.prepare(invocation_state=merged_state)

                        if event.is_callback_event:
                            as_dict = event.as_dict()
                            callback_handler(**as_dict)
                            yield as_dict

                    result = AgentResult(*event["stop"])
                    callback_handler(result=result)
                    yield AgentResultEvent(result=result).as_dict()

                    self._end_agent_trace_span(response=result)

                except Exception as e:
                    self._end_agent_trace_span(error=e)
                    raise

        finally:
            # Clear cancel signal to allow agent reuse after cancellation
</patched>
```

```
<file>src/strands/agent/agent.py</file>
<original>    def __init__(
        self,
        model: Model | str | None = None,
        messages: Messages | None = None,
        tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,
        callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,
        trace_attributes: Mapping[str, AttributeValue] | None = None,
        *,
        agent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: AgentState | dict | None = None,
        plugins: list[Plugin] | None = None,
        hooks: list[HookProvider] | None = None,
        session_manager: SessionManager | None = None,
        structured_output_prompt: str | None = None,
        tool_executor: ToolExecutor | None = None,
        retry_strategy: ModelRetryStrategy | _DefaultRetryStrategySentinel | None = _DEFAULT_RETRY_STRATEGY,
        concurrent_invocation_mode: ConcurrentInvocationMode = ConcurrentInvocationMode.THROW,
    ):
        ...
        self.event_loop_metrics = EventLoopMetrics()
        ...
</original>
<patched>    def __init__(
        self,
        model: Model | str | None = None,
        messages: Messages | None = None,
        tools: list[Union[str, dict[str, str], "ToolProvider", Any]] | None = None,
        system_prompt: str | list[SystemContentBlock] | None = None,
        structured_output_model: type[BaseModel] | None = None,
        callback_handler: Callable[..., Any] | _DefaultCallbackHandlerSentinel | None = _DEFAULT_CALLBACK_HANDLER,
        conversation_manager: ConversationManager | None = None,
        record_direct_tool_call: bool = True,
        load_tools_from_directory: bool = False,
        trace_attributes: Mapping[str, AttributeValue] | None = None,
        *,
        agent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        state: AgentState | dict | None = None,
        plugins: list[Plugin] | None = None,
        hooks: list[HookProvider] | None = None,
        session_manager: SessionManager | None = None,
        structured_output_prompt: str | None = None,
        tool_executor: ToolExecutor | None = None,
        retry_strategy: ModelRetryStrategy | _DefaultRetryStrategySentinel | None = _DEFAULT_RETRY_STRATEGY,
        concurrent_invocation_mode: ConcurrentInvocationMode = ConcurrentInvocationMode.THROW,
    ):
        ...
        self.event_loop_metrics = EventLoopMetrics()
        
    def _compute_messages_token_size(self, messages: Messages) -> int:
        """Compute token size of the list of messages for the current agent context without calling external expensive token counters."""
        # Here, implement an efficient token counting method, for example, by summing lengths of textual content blocks,
        # or by an approximate counting method depending on Messages structure.
        token_size = 0
        for message in messages:
            # Assume message has a 'content' attribute which is list of content blocks
            if hasattr(message, "content") and message.content:
                for block in message.content:
                    # Count tokens in block text if present. Here, roughly count words as tokens.
                    text = getattr(block, "text", "")
                    if text:
                        token_size += len(text.split())
        return token_size
</patched>
```

```
<file>src/strands/telemetry/metrics.py</file>
<original>    def update_usage(self, usage: Usage) -> None:
        """Update the accumulated token usage with new usage data.

        Args:
            usage: The usage data to add to the accumulated totals.
        """
        # Record metrics to OpenTelemetry
        self._metrics_client.event_loop_input_tokens.record(usage["inputTokens"])
        self._metrics_client.event_loop_output_tokens.record(usage["outputTokens"])

        # Handle optional cached token metrics for OpenTelemetry
        if "cacheReadInputTokens" in usage:
            self._metrics_client.event_loop_cache_read_input_tokens.record(usage["cacheReadInputTokens"])
        if "cacheWriteInputTokens" in usage:
            self._metrics_client.event_loop_cache_write_input_tokens.record(usage["cacheWriteInputTokens"])

        self._accumulate_usage(self.accumulated_usage, usage)
        self._accumulate_usage(self.agent_invocations[-1].usage, usage)

        if self.agent_invocations[-1].cycles:
            current_cycle = self.agent_invocations[-1].cycles[-1]
            self._accumulate_usage(current_cycle.usage, usage)
</original>
<patched>    def update_usage(self, usage: Usage) -> None:
        """Update the accumulated token usage with new usage data.

        Args:
            usage: The usage data to add to the accumulated totals.
        """
        # Record metrics to OpenTelemetry
        self._metrics_client.event_loop_input_tokens.record(usage["inputTokens"])
        self._metrics_client.event_loop_output_tokens.record(usage["outputTokens"])

        # Handle optional cached token metrics for OpenTelemetry
        if "cacheReadInputTokens" in usage:
            self._metrics_client.event_loop_cache_read_input_tokens.record(usage["cacheReadInputTokens"])
        if "cacheWriteInputTokens" in usage:
            self._metrics_client.event_loop_cache_write_input_tokens.record(usage["cacheWriteInputTokens"])

        # New: record current agent context tokens if present
        if "currentAgentContextTokens" in usage:
            self._metrics_client.current_agent_context_tokens.record(usage["currentAgentContextTokens"])

        self._accumulate_usage(self.accumulated_usage, usage)
        self._accumulate_usage(self.agent_invocations[-1].usage, usage)

        if self.agent_invocations[-1].cycles:
            current_cycle = self.agent_invocations[-1].cycles[-1]
            self._accumulate_usage(current_cycle.usage, usage)
</patched>
```

```
<file>src/strands/telemetry/metrics.py</file>
<original>    def reset_usage_metrics(self) -> None:
        """Start a new agent invocation by creating a new AgentInvocation.

        This should be called at the start of a new request to begin tracking
        a new agent invocation with fresh usage and cycle data.
        """
        self.agent_invocations.append(AgentInvocation())
</original>
<patched>    def reset_usage_metrics(self) -> None:
        """Start a new agent invocation by creating a new AgentInvocation.

        This should be called at the start of a new request to begin tracking
        a new agent invocation with fresh usage and cycle data.
        """
        self.agent_invocations.append(AgentInvocation())
        # Initialize tracking for current agent context tokens
        self.agent_invocations[-1].usage["currentAgentContextTokens"] = 0
</patched>
```