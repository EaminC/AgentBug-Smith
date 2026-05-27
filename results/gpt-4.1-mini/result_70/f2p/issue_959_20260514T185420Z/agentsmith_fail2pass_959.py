# -*- coding: utf-8 -*-
# mypy: disable-error-code="index"
"""Fail2pass test for issue #959: reset_equipped_tools properly resets tool groups."""

import asyncio
from unittest import IsolatedAsyncioTestCase

from agentscope.message import ToolUseBlock
from agentscope.tool import Toolkit


class TestResetEquippedToolsFail2Pass(IsolatedAsyncioTestCase):
    """Test that reset_equipped_tools resets tool groups correctly.

    Before the fix, calling reset_equipped_tools multiple times to activate
    different tool groups would not deactivate the previously activated groups.
    After the fix, only the explicitly activated groups remain active.
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
        # Initially, no tool groups are active
        self.assertListEqual(self.toolkit.get_json_schemas(), [
            {
                "type": "function",
                "function": {
                    "name": "reset_equipped_tools",
                    "parameters": {
                        "properties": {
                            "group_a": {
                                "type": "boolean",
                                "description": "Tools related to group A.",
                                "default": False,
                            },
                            "group_b": {
                                "type": "boolean",
                                "description": "Tools related to group B.",
                                "default": False,
                            },
                        },
                        "type": "object",
                    },
                    "description": self.toolkit.get_json_schemas()[0]["function"]["description"],
                },
            },
        ])

        # Activate group_a only
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="1",
                name="reset_equipped_tools",
                input={"group_a": True},
            )
        )
        # Collect response text
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        # The response should mention group_a activated and notes included
        self.assertTrue(any("group_a" in t for t in texts))
        self.assertTrue(any("Notes for group A." in t for t in texts))

        # After activation, only group_a tools should appear besides meta tool
        schemas = self.toolkit.get_json_schemas()
        tool_names = {schema["function"]["name"] for schema in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_a", tool_names)
        self.assertNotIn("tool_b", tool_names)

        # Activate group_b only (simulate second call)
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="2",
                name="reset_equipped_tools",
                input={"group_b": True},
            )
        )
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        # The response should mention group_b activated and notes included
        self.assertTrue(any("group_b" in t for t in texts))
        self.assertTrue(any("Notes for group B." in t for t in texts))

        # After activation, only group_b tools should appear besides meta tool
        schemas = self.toolkit.get_json_schemas()
        tool_names = {schema["function"]["name"] for schema in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_b", tool_names)
        self.assertNotIn("tool_a", tool_names)

        # Activate both groups at once
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="3",
                name="reset_equipped_tools",
                input={"group_a": True, "group_b": True},
            )
        )
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        # The response should mention both groups activated and notes included
        self.assertTrue(any("group_a" in t and "group_b" in t for t in texts))
        self.assertTrue(any("Notes for group A." in t for t in texts))
        self.assertTrue(any("Notes for group B." in t for t in texts))

        # After activation, both tool groups should appear besides meta tool
        schemas = self.toolkit.get_json_schemas()
        tool_names = {schema["function"]["name"] for schema in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_a", tool_names)
        self.assertIn("tool_b", tool_names)

        # Deactivate all groups by calling with empty input
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="4",
                name="reset_equipped_tools",
                input={},
            )
        )
        texts = []
        async for chunk in res:
            texts.append(chunk.content[0]["text"])
        # The response should indicate all groups deactivated
        self.assertTrue(any("deactivated" in t for t in texts))

        # After deactivation, only meta tool should appear
        schemas = self.toolkit.get_json_schemas()
        self.assertListEqual(
            schemas,
            [
                {
                    "type": "function",
                    "function": {
                        "name": "reset_equipped_tools",
                        "parameters": {
                            "properties": {
                                "group_a": {
                                    "type": "boolean",
                                    "description": "Tools related to group A.",
                                    "default": False,
                                },
                                "group_b": {
                                    "type": "boolean",
                                    "description": "Tools related to group B.",
                                    "default": False,
                                },
                            },
                            "type": "object",
                        },
                        "description": self.toolkit.get_json_schemas()[0]["function"]["description"],
                    },
                },
            ],
        )

        # Calling a tool from an inactive group should return an error message
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="5",
                name="tool_a",
                input={},
            )
        )
        async for chunk in res:
            self.assertIn(
                "inactive group 'group_a'",
                chunk.content[0]["text"],
            )

    async def asyncTearDown(self) -> None:
        self.toolkit = None
