The issue is caused by a race condition where `_is_session_active` returns True even though the session is effectively closed or shutting down (due to a closed `_close_future`), leading to scheduling calls on an event loop that is no longer able to handle them, which results in indefinite hanging on 4xx/5xx errors.

The proposed fix is to enhance the `_is_session_active` method such that it not only checks whether the background thread is alive but also whether the `_close_future` is still pending. If `_close_future` is done, it means the session is closing or closed, so the method should return False.

This patch minimally modifies only the `_is_session_active` method with the additional check.

---

```
<file>src/strands/tools/mcp/mcp_client.py</file>
<original>    def _is_session_active(self) -> bool:
        return self._background_thread is not None and self._background_thread.is_alive()
</original>
<patched>    def _is_session_active(self) -> bool:
        if self._background_thread is None or not self._background_thread.is_alive():
            return False
        # Check if the close_future has been set and completed, indicating session is closed or closing
        if self._close_future is not None and self._close_future.done():
            return False
        return True
</patched>
```