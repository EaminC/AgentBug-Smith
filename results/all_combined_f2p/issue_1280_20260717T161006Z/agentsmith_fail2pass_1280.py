import sys
from unittest.mock import MagicMock
from unittest import IsolatedAsyncioTestCase

# Mock mcp package and submodules to prevent agentscope/__init__.py from crashing
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

from agentscope.plan import SubTask, Plan, PlanNotebook


class TestRecoverHistoricalPlanHook(IsolatedAsyncioTestCase):
    """Test that recover_historical_plan triggers plan change hooks."""

    async def test_recover_historical_plan_triggers_hook(self) -> None:
        """Test recovering a historical plan triggers plan change hooks."""
        notebook = PlanNotebook()
        hook_calls: list[str | None] = []

        def hook(_nb: PlanNotebook, plan: Plan | None) -> None:
            hook_calls.append(plan.name if plan else None)

        notebook.register_plan_change_hook("recover_hook", hook)

        await notebook.create_plan(
            "P1",
            "desc",
            "outcome",
            [SubTask(name="t1", description="d", expected_outcome="e")],
        )
        await notebook.finish_plan("done", "final")

        self.assertEqual(len(hook_calls), 2)
        self.assertEqual(hook_calls, ["P1", None])

        historical_plan = (await notebook.storage.get_plans())[0]
        await notebook.recover_historical_plan(historical_plan.id)

        # Before fix (PR #1279): hook is not triggered on recover -> len(hook_calls) remains 2 (FAILS)
        # After fix: hook is triggered on recover -> len(hook_calls) is 3 and ends with "P1" (PASSES)
        self.assertEqual(len(hook_calls), 3)
        self.assertEqual(hook_calls[-1], "P1")