The reasoning for the patch is based on the issue where the agent hangs indefinitely on 4xx/5xx errors. The proposed fix in the issue description involves modifying the `_is_session_active` method to not only check if the background thread is alive but also verify if the `_close_future` is done, which indicates that the session is closing or already closed. This additional check prevents scheduling new tasks after the session has begun closing but before the background thread fully exits, avoiding the hanging issue.

We do not need to change other parts of the class because the problem is isolated to the session activity detection logic. The rest of the class handles the threading and async machinery correctly.

Therefore, the patch only modifies the `_is_session_active` method within `MCPClient` to include the `_close_future.done()` check.

```python
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