The issue requests adding support for SEP-1686, which defines long-running tasks in MCP with polling by taskId. To implement this, we need to add suitable new methods to `MCPClient` that enable users to: start a long-running task asynchronously and synchronously, poll the task status by taskId asynchronously and synchronously, and get the final result by taskId.

The existing `call_tool_sync` method currently synchronously calls a tool and returns the immediate response. The natural place to implement the long-running task handling is a new set of `call_tool_*` and `poll_task_*` methods to preserve the existing synchronous and asynchronous APIs and maintain separation of concerns.

We can:
- Add `call_tool_async_task` to start a long-running task asynchronously, returning taskId.
- Add `call_tool_sync_task` wrapping the async method and then polling the task status (polling loop inside), returning the final result synchronously.
- Add `poll_task_async` which polls the status of an ongoing task asynchronously.
- Add `poll_task_sync` which wraps the async polling call synchronously.

These will internally call respective session async methods on the background thread (via `_invoke_on_background_thread`).

This approach cleanly extends the MCPClient with the task feature, does not disrupt existing code, and leverages the existing background thread communication mechanisms.

---

Patch:

```python
<file>src/strands/tools/mcp/mcp_client.py</file>
<original>    def call_tool_sync(
        self,
        tool_use_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
    ) -> MCPToolResult:
        """Synchronously calls a tool on the MCP server.

        This method calls the asynchronous call_tool method on the MCP session
        and converts the result to the ToolResult format. If the MCP tool returns
        structured content, it will be included as the last item in the content array
        of the returned ToolResult.

        Args:
            tool_use_id: Unique identifier for this tool use
            name: Name of the tool to call
            arguments: Optional arguments to pass to the tool
            read_timeout_seconds: Optional timeout for the tool call

        Returns:
            MCPToolResult: The result of the tool call
        """
        self._log_debug_with_thread("calling MCP tool '%s' synchronously with tool_use_id=%s", name, tool_use_id)
        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        async def _call_tool_async() -> MCPCallToolResult:
            return await cast(ClientSession, self._background_thread_session).call_tool(
                name, arguments, read_timeout_seconds
            )

        try:
            call_tool_result: MCPCallToolResult = self._invoke_on_background_thread(_call_tool_async()).result()
            return self._handle_tool_result(tool_use_id, call_tool_result)
        except Exception as e:
            logger.exception("tool execution failed")
            return self._handle_tool_execution_error(tool_use_id, e)
</original>
<patched>    def call_tool_sync(
        self,
        tool_use_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
    ) -> MCPToolResult:
        """Synchronously calls a tool on the MCP server.

        This method calls the asynchronous call_tool method on the MCP session
        and converts the result to the ToolResult format. If the MCP tool returns
        structured content, it will be included as the last item in the content array
        of the returned ToolResult.

        Args:
            tool_use_id: Unique identifier for this tool use
            name: Name of the tool to call
            arguments: Optional arguments to pass to the tool
            read_timeout_seconds: Optional timeout for the tool call

        Returns:
            MCPToolResult: The result of the tool call
        """
        self._log_debug_with_thread("calling MCP tool '%s' synchronously with tool_use_id=%s", name, tool_use_id)
        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        async def _call_tool_async() -> MCPCallToolResult:
            return await cast(ClientSession, self._background_thread_session).call_tool(
                name, arguments, read_timeout_seconds
            )

        try:
            call_tool_result: MCPCallToolResult = self._invoke_on_background_thread(_call_tool_async()).result()
            return self._handle_tool_result(tool_use_id, call_tool_result)
        except Exception as e:
            logger.exception("tool execution failed")
            return self._handle_tool_execution_error(tool_use_id, e)

    def call_tool_sync_task(
        self,
        tool_use_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
        poll_interval_seconds: float = 1.0,
        read_timeout_seconds: timedelta | None = None,
    ) -> MCPToolResult:
        """
        Synchronously starts a long-running MCP task and polls until it's complete.

        Args:
            tool_use_id: Unique identifier for this tool use
            name: Name of the tool to call
            arguments: Optional arguments to pass to the tool
            poll_interval_seconds: Interval in seconds between polls
            read_timeout_seconds: Optional timeout for the initial tool call

        Returns:
            MCPToolResult: The final result of the task
        """
        import time

        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        try:
            # Start the task asynchronously to get the task_id
            task_id = self.call_tool_async_task(tool_use_id, name, arguments, read_timeout_seconds).result()
            self._log_debug_with_thread("started task with task_id=%s for tool_use_id=%s", task_id, tool_use_id)

            # Poll the task status until finished
            while True:
                task_result = self.poll_task_sync(tool_use_id, task_id)
                if task_result.status != "running":
                    return task_result
                time.sleep(poll_interval_seconds)
        except Exception as e:
            logger.exception("task execution failed")
            return self._handle_tool_execution_error(tool_use_id, e)

    async def call_tool_async_task(
        self,
        tool_use_id: str,
        name: str,
        arguments: dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
    ) -> str:
        """
        Asynchronously starts a long-running MCP task and returns the taskId.

        Args:
            tool_use_id: Unique identifier for this tool use
            name: Name of the tool to call
            arguments: Optional arguments to pass to the tool
            read_timeout_seconds: Optional timeout for the tool call

        Returns:
            str: The taskId for the started long-running task
        """
        self._log_debug_with_thread("starting async MCP task '%s' with tool_use_id=%s", name, tool_use_id)
        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        async def _call_tool_async() -> str:
            session = cast(ClientSession, self._background_thread_session)
            # The actual call_task should return the taskId
            task_id = await session.call_tool_async_task(name, arguments, read_timeout_seconds)
            return task_id

        future = self._invoke_on_background_thread(_call_tool_async())
        return await asyncio.wrap_future(future)

    def poll_task_sync(self, tool_use_id: str, task_id: str) -> MCPToolResult:
        """
        Synchronously polls a long-running MCP task and returns its current status/result.

        Args:
            tool_use_id: Unique identifier for this tool use
            task_id: The MCP taskId to poll

        Returns:
            MCPToolResult: The current result/status of the task
        """
        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        async def _poll_task_async() -> MCPCallToolResult:
            session = cast(ClientSession, self._background_thread_session)
            return await session.poll_task(task_id)

        try:
            call_tool_result = self._invoke_on_background_thread(_poll_task_async()).result()
            return self._handle_tool_result(tool_use_id, call_tool_result)
        except Exception as e:
            logger.exception("task polling failed")
            return self._handle_tool_execution_error(tool_use_id, e)

    async def poll_task_async(self, tool_use_id: str, task_id: str) -> MCPToolResult:
        """
        Asynchronously polls a long-running MCP task and returns its current status/result.

        Args:
            tool_use_id: Unique identifier for this tool use
            task_id: The MCP taskId to poll

        Returns:
            MCPToolResult: The current result/status of the task
        """
        self._log_debug_with_thread("async polling MCP task with task_id=%s for tool_use_id=%s", task_id, tool_use_id)
        if not self._is_session_active():
            raise MCPClientInitializationError(CLIENT_SESSION_NOT_RUNNING_ERROR_MESSAGE)

        async def _poll_task_async() -> MCPCallToolResult:
            session = cast(ClientSession, self._background_thread_session)
            return await session.poll_task(task_id)

        try:
            future = self._invoke_on_background_thread(_poll_task_async())
            call_tool_result: MCPCallToolResult = await asyncio.wrap_future(future)
            return self._handle_tool_result(tool_use_id, call_tool_result)
        except Exception as e:
            logger.exception("task polling failed")
            return self._handle_tool_execution_error(tool_use_id, e)
</patched>
```