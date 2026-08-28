# -*- coding: utf-8 -*-
# mypy: disable-error-code="index"
"""Fail2pass test for issue #959: reset_equipped_tools properly resets tool groups."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
from unittest import IsolatedAsyncioTestCase

# 1. Force workspace source priority
src_dir = str(Path("/app/src").resolve())
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 2. Mock mcp package and submodules before ANY agentscope import
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

# 3. Import AgentScope message and tool components
from agentscope.message import ToolUseBlock
from agentscope.tool import Toolkit


class TestResetEquippedToolsFail2Pass(IsolatedAsyncioTestCase):
    """Test that reset_equipped_tools resets tool groups correctly.

    Before the fix (PR #962), calling reset_equipped_tools multiple times to activate
    different tool groups would not deactivate previously activated groups.
    After the fix, each call sets the absolute final state, deactivating other groups.
    """

    async def asyncSetUp(self) -> None:
        self.toolkit = Toolkit()
        # Register the reset_equipped_tools meta tool
        self.toolkit.register_tool_function(self.toolkit.reset_equipped_tools)

        # Create two tool groups with notes
        self.toolkit.create_tool_group(
            "group_a",
            "Tools related to group A.",
            notes="Notes for group A.",
        )
        self.toolkit.create_tool_group(
            "group_b",
            "Tools related to group B.",
            notes="Notes for group B.",
        )

        # Register dummy tool functions in each group
        def tool_a() -> None:
            return None

        def tool_b() -> None:
            return None

        self.toolkit.register_tool_function(tool_a, group_name="group_a")
        self.toolkit.register_tool_function(tool_b, group_name="group_b")

    async def test_reset_equipped_tools_resets_groups(self) -> None:
        # 1. Activate group_a only
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="1",
                name="reset_equipped_tools",
                input={"group_a": True},
            ),
        )
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        self.assertTrue(any("group_a" in t for t in texts))

        schemas = self.toolkit.get_json_schemas()
        tool_names = {schema["function"]["name"] for schema in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_a", tool_names)
        self.assertNotIn("tool_b", tool_names)

        # 2. Activate group_b only (second call)
        # Pre-patch: group_a was NOT deactivated, so tool_a remained in schemas (FAILS rc1=1)
        # Post-patch: group_a IS deactivated, so only tool_b and meta tool are active (PASSES rc2=0)
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="2",
                name="reset_equipped_tools",
                input={"group_b": True},
            ),
        )
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        self.assertTrue(any("group_b" in t for t in texts))

        schemas = self.toolkit.get_json_schemas()
        tool_names = {schema["function"]["name"] for schema in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_b", tool_names)
        self.assertNotIn("tool_a", tool_names)

        # 3. Calling an inactive group's tool function returns FunctionInactiveError
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="3",
                name="tool_a",
                input={},
            ),
        )
        async for chunk in res:
            self.assertIn(
                "inactive group 'group_a'",
                chunk.content[0]["text"],
            )

    async def asyncTearDown(self) -> None:
        self.toolkit = None