The issue is that the method `recover_historical_plan` sets `self.current_plan` to the recovered historical plan but does not trigger the plan change hooks afterward, leaving observers/UI not updated about the plan change. The fix is straightforward: after assigning the recovered plan to `self.current_plan`, call `await self._trigger_plan_change_hooks()` to notify all registered hooks.

This keeps the change minimal and consistent with how other methods like `create_plan` and `finish_plan` handle plan change notifications.

---

```
<file>src/agentscope/plan/_plan_notebook.py</file>
<original>    async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
        """Recover a historical plan by given plan ID, the plan ID can be
        obtained by calling `view_historical_plans`. Note the recover
        operation will override the current plan if exists.

        Args:
            plan_id (`str`):
                The ID of the historical plan to be recovered.
        """
        historical_plan = await self.storage.get_plan(plan_id)
        if historical_plan is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Cannot find the plan with ID '{plan_id}'.",
                    ),
                ],
            )

        # Store the current plan into history if exists
        if self.current_plan:
            if self.current_plan.state != "done":
                self.current_plan.finish(
                    "abandoned",
                    f"The plan execution is interrupted by a new plan "
                    f"with ID '{historical_plan.id}'.",
                )
            await self.storage.add_plan(self.current_plan)
            res = ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "The current plan named "
                            f"'{self.current_plan.name}' is replaced by the "
                            f"historical plan named '{historical_plan.name}' "
                            f"with ID '{historical_plan.id}'."
                        ),
                    ),
                ],
            )
        else:
            res = ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            f"Historical plan named '{historical_plan.name}' "
                            f"with ID '{historical_plan.id}' is recovered "
                            "successfully."
                        ),
                    ),
                ],
            )
        self.current_plan = historical_plan
        return res
</original>
<patched>    async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
        """Recover a historical plan by given plan ID, the plan ID can be
        obtained by calling `view_historical_plans`. Note the recover
        operation will override the current plan if exists.

        Args:
            plan_id (`str`):
                The ID of the historical plan to be recovered.
        """
        historical_plan = await self.storage.get_plan(plan_id)
        if historical_plan is None:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"Cannot find the plan with ID '{plan_id}'.",
                    ),
                ],
            )

        # Store the current plan into history if exists
        if self.current_plan:
            if self.current_plan.state != "done":
                self.current_plan.finish(
                    "abandoned",
                    f"The plan execution is interrupted by a new plan "
                    f"with ID '{historical_plan.id}'.",
                )
            await self.storage.add_plan(self.current_plan)
            res = ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            "The current plan named "
                            f"'{self.current_plan.name}' is replaced by the "
                            f"historical plan named '{historical_plan.name}' "
                            f"with ID '{historical_plan.id}'."
                        ),
                    ),
                ],
            )
        else:
            res = ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=(
                            f"Historical plan named '{historical_plan.name}' "
                            f"with ID '{historical_plan.id}' is recovered "
                            "successfully."
                        ),
                    ),
                ],
            )
        self.current_plan = historical_plan
        await self._trigger_plan_change_hooks()
        return res
</patched>
```