from unittest import IsolatedAsyncioTestCase

from agentscope.message import ToolUseBlock, TextBlock
from agentscope.tool import ToolResponse, Toolkit


def tool_function_1() -> ToolResponse:
    """Test tool function 1."""
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text="tool1_result",
            ),
        ],
    )


def tool_function_2() -> ToolResponse:
    """Test tool function 2."""
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text="tool2_result",
            ),
        ],
    )


class TestResetEquippedToolsDeactivation(IsolatedAsyncioTestCase):
    """Test that reset_equipped_tools properly deactivates previously activated groups."""

    async def asyncSetUp(self) -> None:
        """Set up the test environment before each test."""
        self.toolkit = Toolkit()

        # Register the meta tool
        self.toolkit.register_tool_function(
            self.toolkit.reset_equipped_tools,
        )

        # Create first tool group and register a tool
        self.toolkit.create_tool_group(
            "group_a",
            "Group A tools.",
        )
        self.toolkit.register_tool_function(
            tool_function_1,
            group_name="group_a",
        )

        # Create second tool group and register a tool
        self.toolkit.create_tool_group(
            "group_b",
            "Group B tools.",
        )
        self.toolkit.register_tool_function(
            tool_function_2,
            group_name="group_b",
        )

    async def test_reset_deactivates_previous_groups(self) -> None:
        """Test that calling reset_equipped_tools deactivates previously activated groups."""
        # Activate group_a
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="1",
                name="reset_equipped_tools",
                input={"group_a": True},
            ),
        )

        async for chunk in res:
            self.assertIn("group_a", chunk.content[0]["text"])

        # Verify group_a tool is available
        schemas = self.toolkit.get_json_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertIn("tool_function_1", tool_names)
        self.assertNotIn("tool_function_2", tool_names)

        # Now activate only group_b - this should deactivate group_a
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="2",
                name="reset_equipped_tools",
                input={"group_b": True},
            ),
        )

        async for chunk in res:
            self.assertIn("group_b", chunk.content[0]["text"])

        # Verify group_a tool is NOT available anymore (key assertion for the bug)
        schemas = self.toolkit.get_json_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertNotIn("tool_function_1", tool_names)
        self.assertIn("tool_function_2", tool_names)

        # Try to call tool_function_1 from deactivated group_a
        # This should return an error indicating the function is inactive
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="3",
                name="tool_function_1",
                input={},
            ),
        )

        async for chunk in res:
            self.assertIn("FunctionInactiveError", chunk.content[0]["text"])
            self.assertIn("inactive group 'group_a'", chunk.content[0]["text"])

    async def test_reset_with_empty_deactivates_all(self) -> None:
        """Test that calling reset_equipped_tools with no arguments deactivates all groups."""
        # Activate both groups
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="1",
                name="reset_equipped_tools",
                input={"group_a": True, "group_b": True},
            ),
        )

        async for chunk in res:
            self.assertIn("group_a", chunk.content[0]["text"])
            self.assertIn("group_b", chunk.content[0]["text"])

        # Verify both tools are available
        schemas = self.toolkit.get_json_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertIn("tool_function_1", tool_names)
        self.assertIn("tool_function_2", tool_names)

        # Now reset with empty arguments - should deactivate all
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="2",
                name="reset_equipped_tools",
                input={},
            ),
        )

        async for chunk in res:
            self.assertEqual(
                chunk.content[0]["text"],
                "All tool groups are now deactivated currently.",
            )

        # Verify no tools are available (only meta tool remains)
        schemas = self.toolkit.get_json_schemas()
        tool_names = [s["function"]["name"] for s in schemas]
        self.assertNotIn("tool_function_1", tool_names)
        self.assertNotIn("tool_function_2", tool_names)

    async def asyncTearDown(self) -> None:
        """Clean up after each test."""
        self.toolkit = None
