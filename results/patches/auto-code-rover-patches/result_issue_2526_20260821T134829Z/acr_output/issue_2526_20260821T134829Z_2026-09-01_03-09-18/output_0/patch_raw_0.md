Reasoning:

The issue requests porting over the `Agent.invoke({invocationState})` method from the Python SDK and plumbing the invocationState through hooks and toolContext.

Looking at the existing `Agent` class, there is an `__call__`, an async `invoke_async`, and `stream_async` methods which deal with invocation, but there is no direct `invoke` method as requested. To keep with the new interface consistent with the Python SDK, we should add a new `invoke(self, prompt, **invocation_state)` method to the `Agent` class. This method will accept an `invocationState` parameter and pass it through the agent's invocation lifecycle, including hooks, and passing it down to the event loop.

Since the async infrastructure already accepts `invocation_state` as a dict in `_run_loop` and the `stream_async` method accepts kwargs to pass to the event loop, we can reuse this plumbing.

We also must update the `ToolCaller.__getattr__`'s `caller()` to accept an `invocation_state` parameter to pass to `run_tool` if possible, but since the current tool calling uses kwargs as input for the tool invocation, and `run_tool` also accepts the invocation_state (actually passing kwargs as invocation_state currently), that seems already addressed (kwargs are being passed on as an `invocation_state`). So no change needed there.

Finally, the `_record_tool_execution` method can remain unchanged; no specific changes to handle invocation_state are required unless we want to include invocation_state data in the recorded messages. The prompt and user_message_override is already used to create detailed user messages.

Therefore, the essential change is to add an `invoke()` method to the `Agent` class that accepts a prompt and invocationState dict, and prunes to the existing plumbing.

---

Patch:

```
<file>src/strands/agent/agent.py</file>
<original>    
    def __call__(self, prompt: Union[str, list[ContentBlock]], **kwargs: Any) -> AgentResult:
        """Process a natural language prompt through the agent's event loop.

        This method implements the conversational interface (e.g., `agent("hello!")`). It adds the user's prompt to
        the conversation history, processes it through the model, executes any tool calls, and returns the final result.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            **kwargs: Additional parameters to pass through the event loop.

        Returns:
            Result object containing:

                - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                - message: The final message from the model
                - metrics: Performance metrics from the event loop
                - state: The final state of the event loop
        """

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **kwargs))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()
</original>
<patched>    
    def __call__(self, prompt: Union[str, list[ContentBlock]], **kwargs: Any) -> AgentResult:
        """Process a natural language prompt through the agent's event loop.

        This method implements the conversational interface (e.g., `agent("hello!")`). It adds the user's prompt to
        the conversation history, processes it through the model, executes any tool calls, and returns the final result.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            **kwargs: Additional parameters to pass through the event loop.

        Returns:
            Result object containing:

                - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                - message: The final message from the model
                - metrics: Performance metrics from the event loop
                - state: The final state of the event loop
        """

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **kwargs))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()

    def invoke(self, prompt: Union[str, list[ContentBlock]], invocation_state: Optional[dict[str, Any]] = None) -> AgentResult:
        """Synchronous invoke method ported from Python SDK.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            invocation_state: Optional dict of additional state and context to pass through the invocation lifecycle.

        Returns:
            Result object containing the final state of the event loop.
        """
        if invocation_state is None:
            invocation_state = {}

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **invocation_state))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()
</patched>
</file>
```

---

This patch adds the `invoke` method that accepts a prompt and invocation_state dict and invokes the agent lifecycle with the extra plumbing, consistent with the Python SDK approach. It reuses the existing async `invoke_async` method and passes invocation_state as kwargs.

No other changes were needed since the existing `_run_loop` and `_execute_event_loop_cycle` accept and propagate invocation_state, and tool caller already passes kwargs as invocation_state during tool calls.

# Final patch:

```
<file>src/strands/agent/agent.py</file>
<original>    
    def __call__(self, prompt: Union[str, list[ContentBlock]], **kwargs: Any) -> AgentResult:
        """Process a natural language prompt through the agent's event loop.

        This method implements the conversational interface (e.g., `agent("hello!")`). It adds the user's prompt to
        the conversation history, processes it through the model, executes any tool calls, and returns the final result.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            **kwargs: Additional parameters to pass through the event loop.

        Returns:
            Result object containing:

                - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                - message: The final message from the model
                - metrics: Performance metrics from the event loop
                - state: The final state of the event loop
        """

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **kwargs))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()
</original>
<patched>    
    def __call__(self, prompt: Union[str, list[ContentBlock]], **kwargs: Any) -> AgentResult:
        """Process a natural language prompt through the agent's event loop.

        This method implements the conversational interface (e.g., `agent("hello!")`). It adds the user's prompt to
        the conversation history, processes it through the model, executes any tool calls, and returns the final result.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            **kwargs: Additional parameters to pass through the event loop.

        Returns:
            Result object containing:

                - stop_reason: Why the event loop stopped (e.g., "end_turn", "max_tokens")
                - message: The final message from the model
                - metrics: Performance metrics from the event loop
                - state: The final state of the event loop
        """

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **kwargs))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()

    def invoke(self, prompt: Union[str, list[ContentBlock]], invocation_state: Optional[dict[str, Any]] = None) -> AgentResult:
        """Synchronous invoke method ported from Python SDK.

        Args:
            prompt: User input as text or list of ContentBlock objects for multi-modal content.
            invocation_state: Optional dict of additional state and context to pass through the invocation lifecycle.

        Returns:
            Result object containing the final state of the event loop.
        """
        if invocation_state is None:
            invocation_state = {}

        def execute() -> AgentResult:
            return asyncio.run(self.invoke_async(prompt, **invocation_state))

        with ThreadPoolExecutor() as executor:
            future = executor.submit(execute)
            return future.result()
</patched>
</file>
```