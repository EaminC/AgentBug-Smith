The issue here is that the method `recover_historical_plan` updates `self.current_plan` to the recovered historical plan, but it does not trigger the `_trigger_plan_change_hooks()` method afterward, unlike other places where `current_plan` is updated. Since this method is async, we should make it async and `await` the triggering of hooks to notify any listeners about the change.

This is a minimal change that adds the `await self._trigger_plan_change_hooks()` call after setting `self.current_plan = historical_plan` but before returning. This ensures all plan change hooks are executed after recovering a plan, keeping consistent behavior across plan state changes.

---

# modification 1
```
<file>src/agentscope/plan/_plan_notebook.py</file>
<original>    async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
        ...
        self.current_plan = historical_plan
        return res
</original>
<patched>    async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
        ...
        self.current_plan = historical_plan
        await self._trigger_plan_change_hooks()
        return res
</patched>
```