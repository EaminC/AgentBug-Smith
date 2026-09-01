The issue described is that the MCPClient agent hangs indefinitely when there are 4xx/5xx errors. From the investigation and the provided patch, the root cause stems from a race condition where tasks are scheduled after an exception causes the session to be closed (signified by `_close_future` being completed), but before the background thread itself has fully terminated. During this window, the existing `_is_session_active` method returns True (if the background thread is alive), which leads to scheduling tasks on an event loop that is no longer functional, causing these tasks (and thus the agent) to hang forever.

The fix is to enhance `_is_session_active` to also check if `_close_future` is done. `_close_future` being done indicates that the session is actually closed / shutting down even if the thread is still alive momentarily. This prevents new tasks from being scheduled to this "closed" session.

Therefore, the minimal and effective fix is to update the `_is_session_active` method, preserving existing logic but adding the check against `_close_future.done()`.

No other modifications are needed since the rest of the client code depends on `_is_session_active` for determining if it can proceed with scheduling tasks.

---

# modification 1
```
<file>src/strands/tools/mcp/mcp_client.py</file>
<original>803     def _is_session_active(self) -> bool:
804         return self._background_thread is not None and self._background_thread.is_alive()
</original>
<patched>803     def _is_session_active(self) -> bool:
804         if self._background_thread is None or not self._background_thread.is_alive():
805             return False
806         if self._close_future is not None and self._close_future.done():
807             return False
808         return True
</patched>
```