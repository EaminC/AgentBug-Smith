The problem is that the `InitializeResult` returned by `session.initialize()` inside `_async_background_thread` is currently awaited but its result is discarded. The instructions field inside that result holds useful server instructions per the MCP spec that should be exposed to the user of `MCPClient`.

The fix is straightforward: assign the awaited `session.initialize()` to a variable, then save `result.instructions` (defaulting to empty string if `None`) into a new instance attribute `self.server_instructions`. This exposes the instructions to host applications in a simple, non-intrusive way.

This change does not alter any other behavior. It adds a public attribute `server_instructions` to MCPClient for use by host applications.

# modification 1
```
<file>src/strands/tools/mcp/mcp_client.py</file>
<original>    async def _async_background_thread(self) -> None:
        """Asynchronous method that runs in the background thread to manage the MCP connection.

        This method establishes the transport connection, creates and initializes the MCP session,
        signals readiness to the main thread, and waits for a close signal.
        """
        self._log_debug_with_thread("starting async background thread for MCP connection")

        # Initialized here so that it has the asyncio loop
        self._close_future = asyncio.Future()

        try:
            async with self._transport_callable() as (read_stream, write_stream, *_):
                self._log_debug_with_thread("transport connection established")
                async with ClientSession(
                    read_stream,
                    write_stream,
                    message_handler=self._handle_error_message,
                    elicitation_callback=self._elicitation_callback,
                ) as session:
                    self._log_debug_with_thread("initializing MCP session")
                    await session.initialize()

                    self._log_debug_with_thread("session initialized successfully")
                    # Store the session for use while we await the close event
                    self._background_thread_session = session

                    # Cache server task capability immediately after initialization
                    # Capabilities are exchanged during session.initialize(), so this is available now
                    caps = session.get_server_capabilities()
                    self._server_task_capable = (
                        caps is not None
                        and caps.tasks is not None
                        and caps.tasks.requests is not None
                        and caps.tasks.requests.tools is not None
                        and caps.tasks.requests.tools.call is not None
                    )
                    self._log_debug_with_thread(
                        "server_task_capable=<%s> | cached server task capability", self._server_task_capable
                    )

                    # Signal that the session has been created and is ready for use
                    self._init_future.set_result(None)

                    self._log_debug_with_thread("waiting for close signal")
                    # Keep background thread running until signaled to close.
                    # Thread is not blocked as this a future
                    await self._close_future

                    self._log_debug_with_thread("close signal received")
        except Exception as e:
            # If we encounter an exception and the future is still running,
            # it means it was encountered during the initialization phase.
            if not self._init_future.done():
                self._init_future.set_exception(e)
            else:
                # _close_future is automatically cancelled by the framework which doesn't provide us with the useful
                # exception, so instead we store the exception in a different field where stop() can read it
                self._close_exception = e
                if self._close_future and not self._close_future.done():
                    self._close_future.set_result(None)

                self._log_debug_with_thread(
                    "encountered exception on background thread after initialization %s", str(e)
                )</original>
<patched>    async def _async_background_thread(self) -> None:
        """Asynchronous method that runs in the background thread to manage the MCP connection.

        This method establishes the transport connection, creates and initializes the MCP session,
        signals readiness to the main thread, and waits for a close signal.
        """
        self._log_debug_with_thread("starting async background thread for MCP connection")

        # Initialized here so that it has the asyncio loop
        self._close_future = asyncio.Future()

        try:
            async with self._transport_callable() as (read_stream, write_stream, *_):
                self._log_debug_with_thread("transport connection established")
                async with ClientSession(
                    read_stream,
                    write_stream,
                    message_handler=self._handle_error_message,
                    elicitation_callback=self._elicitation_callback,
                ) as session:
                    self._log_debug_with_thread("initializing MCP session")
                    result = await session.initialize()
                    self.server_instructions = result.instructions or ""

                    self._log_debug_with_thread("session initialized successfully")
                    # Store the session for use while we await the close event
                    self._background_thread_session = session

                    # Cache server task capability immediately after initialization
                    # Capabilities are exchanged during session.initialize(), so this is available now
                    caps = session.get_server_capabilities()
                    self._server_task_capable = (
                        caps is not None
                        and caps.tasks is not None
                        and caps.tasks.requests is not None
                        and caps.tasks.requests.tools is not None
                        and caps.tasks.requests.tools.call is not None
                    )
                    self._log_debug_with_thread(
                        "server_task_capable=<%s> | cached server task capability", self._server_task_capable
                    )

                    # Signal that the session has been created and is ready for use
                    self._init_future.set_result(None)

                    self._log_debug_with_thread("waiting for close signal")
                    # Keep background thread running until signaled to close.
                    # Thread is not blocked as this a future
                    await self._close_future

                    self._log_debug_with_thread("close signal received")
        except Exception as e:
            # If we encounter an exception and the future is still running,
            # it means it was encountered during the initialization phase.
            if not self._init_future.done():
                self._init_future.set_exception(e)
            else:
                # _close_future is automatically cancelled by the framework which doesn't provide us with the useful
                # exception, so instead we store the exception in a different field where stop() can read it
                self._close_exception = e
                if self._close_future and not self._close_future.done():
                    self._close_future.set_result(None)

                self._log_debug_with_thread(
                    "encountered exception on background thread after initialization %s", str(e)
                )</patched>
```