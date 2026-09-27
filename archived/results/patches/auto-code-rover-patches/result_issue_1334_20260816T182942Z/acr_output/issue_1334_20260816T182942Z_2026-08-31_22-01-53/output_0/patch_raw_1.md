The issue involves the agent hanging indefinitely on 5xx errors because the `_is_session_active()` method does not consider the state of `_close_future`. This can result in a race condition where tasks are scheduled after the session is technically closing but before the background thread has exited. To fix this, we need to modify `_is_session_active()` to also check if `_close_future` is done and return False in that case. This prevents new tasks from being scheduled when the session is closing or closed, thus avoiding the indefinite hangs.

This is a minimal patch that only modifies `_is_session_active()` method to add the additional check. It retains the existing behavior if the background thread is alive and `_close_future` is not done.

# modification 1
```
<file>src/strands/tools/mcp/mcp_client.py</file>
<original>803     def _is_session_active(self) -> bool:
804         return self._background_thread is not None and self._background_thread.is_alive()
</original>
<patched>803     def _is_session_active(self) -> bool:
804         if self._background_thread is None or not self._background_thread.is_alive():
805             return False
806         # Check if the close_future has been set and is done, indicating session is closing/closed
807         if self._close_future is not None and self._close_future.done():
808             return False
809         return True
</patched>
```