The issue is that when `recover_historical_plan` sets `self.current_plan` to the recovered historical plan, it does not trigger the plan change hooks by calling `_trigger_plan_change_hooks()`. This causes observers relying on these hooks to miss the update.

The fix is minimal: after setting `self.current_plan = historical_plan`, we should call `await self._trigger_plan_change_hooks()` to notify all registered hooks about the plan change. Since `_trigger_plan_change_hooks` is asynchronous, `recover_historical_plan` must also be asynchronous, which it already is.

This preserves existing functionality while notifying observers about plan recovery, solving the issue as described.

---

```
<file>src/agentscope/plan/_plan_notebook.py</file>
<original>762     async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
763         """Recover a historical plan by given plan ID, the plan ID can be
764         obtained by calling `view_historical_plans`. Note the recover
765         operation will override the current plan if exists.
766 
767         Args:
768             plan_id (`str`):
769                 The ID of the historical plan to be recovered.
770         """
771         historical_plan = await self.storage.get_plan(plan_id)
772         if historical_plan is None:
773             return ToolResponse(
774                 content=[
775                     TextBlock(
776                         type="text",
777                         text=f"Cannot find the plan with ID '{plan_id}'.",
778                     ),
779                 ],
780             )
781 
782         # Store the current plan into history if exists
783         if self.current_plan:
784             if self.current_plan.state != "done":
785                 self.current_plan.finish(
786                     "abandoned",
787                     f"The plan execution is interrupted by a new plan "
788                     f"with ID '{historical_plan.id}'.",
789                 )
790             await self.storage.add_plan(self.current_plan)
791             res = ToolResponse(
792                 content=[
793                     TextBlock(
794                         type="text",
795                         text=(
796                             "The current plan named "
797                             f"'{self.current_plan.name}' is replaced by the "
798                             f"historical plan named '{historical_plan.name}' "
799                             f"with ID '{historical_plan.id}'."
800                         ),
801                     ),
802                 ],
803             )
804         else:
805             res = ToolResponse(
806                 content=[
807                     TextBlock(
808                         type="text",
809                         text=(
810                             f"Historical plan named '{historical_plan.name}' "
811                             f"with ID '{historical_plan.id}' is recovered "
812                             "successfully."
813                         ),
814                     ),
815                 ],
816             )
817         self.current_plan = historical_plan
818         return res</original>
<patched>762     async def recover_historical_plan(self, plan_id: str) -> ToolResponse:
763         """Recover a historical plan by given plan ID, the plan ID can be
764         obtained by calling `view_historical_plans`. Note the recover
765         operation will override the current plan if exists.
766 
767         Args:
768             plan_id (`str`):
769                 The ID of the historical plan to be recovered.
770         """
771         historical_plan = await self.storage.get_plan(plan_id)
772         if historical_plan is None:
773             return ToolResponse(
774                 content=[
775                     TextBlock(
776                         type="text",
777                         text=f"Cannot find the plan with ID '{plan_id}'.",
778                     ),
779                 ],
780             )
781 
782         # Store the current plan into history if exists
783         if self.current_plan:
784             if self.current_plan.state != "done":
785                 self.current_plan.finish(
786                     "abandoned",
787                     f"The plan execution is interrupted by a new plan "
788                     f"with ID '{historical_plan.id}'.",
789                 )
790             await self.storage.add_plan(self.current_plan)
791             res = ToolResponse(
792                 content=[
793                     TextBlock(
794                         type="text",
795                         text=(
796                             "The current plan named "
797                             f"'{self.current_plan.name}' is replaced by the "
798                             f"historical plan named '{historical_plan.name}' "
799                             f"with ID '{historical_plan.id}'."
800                         ),
801                     ),
802                 ],
803             )
804         else:
805             res = ToolResponse(
806                 content=[
807                     TextBlock(
808                         type="text",
809                         text=(
810                             f"Historical plan named '{historical_plan.name}' "
811                             f"with ID '{historical_plan.id}' is recovered "
812                             "successfully."
813                         ),
814                     ),
815                 ],
816             )
817         self.current_plan = historical_plan
818         await self._trigger_plan_change_hooks()
819         return res</patched>
```