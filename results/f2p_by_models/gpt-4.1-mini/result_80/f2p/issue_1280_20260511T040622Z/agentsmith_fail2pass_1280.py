# -*- coding: utf-8 -*-
"""Fail2pass test for issue #1280: recover_historical_plan triggers plan change hooks."""

import asyncio
import unittest

from agentscope.plan import PlanNotebook, SubTask, Plan


class TestRecoverHistoricalPlanHooks(unittest.IsolatedAsyncioTestCase):
    async def test_recover_historical_plan_triggers_hook(self) -> None:
        """Test that recovering a historical plan triggers plan change hooks."""
        notebook = PlanNotebook()
        hook_calls: list[str | None] = []

        def hook(_nb: PlanNotebook, plan: Plan | None) -> None:
            hook_calls.append(plan.name if plan else None)

        notebook.register_plan_change_hook("recover_hook", hook)

        # Create a plan and then finish it to archive it
        await notebook.create_plan(
            "P1",
            "desc",
            "outcome",
            [SubTask(name="t1", description="d", expected_outcome="e")],
        )
        await notebook.finish_plan("done", "final")

        # After create_plan and finish_plan, hooks should have been called twice
        self.assertEqual(len(hook_calls), 2)
        self.assertEqual(hook_calls, ["P1", None])

        # Get the historical plan id and recover it
        historical_plan = (await notebook.storage.get_plans())[0]
        await notebook.recover_historical_plan(historical_plan.id)

        # After recovering, the hook should be called once more with the plan name
        self.assertEqual(len(hook_calls), 3)
        self.assertEqual(hook_calls[-1], "P1")


if __name__ == "__main__":
    unittest.main()
