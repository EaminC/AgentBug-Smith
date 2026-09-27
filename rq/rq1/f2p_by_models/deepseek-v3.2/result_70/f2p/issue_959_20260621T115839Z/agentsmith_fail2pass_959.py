from unittest import IsolatedAsyncioTestCase

from agentscope.message import ToolUseBlock, TextBlock
from agentscope.tool import ToolResponse, Toolkit


def dummy_tool() -> ToolResponse:
    """A dummy tool for testing."""
    return ToolResponse(
        content=[
            TextBlock(
                type="text",
                text="dummy",
            ),
        ],
    )


class TestResetEquippedToolsPersistentActivation(IsolatedAsyncioTestCase):
    """Test that reset_equipped_tools properly handles activation/deactivation."""

    async def asyncSetUp(self) -> None:
        """Set up the test environment before each test."""
        self.toolkit = Toolkit()

    async def asyncTearDown(self) -> None:
        """Clean up after each test."""
        self.toolkit = None

    async def test_reset_equipped_tools_resets_all_groups(self) -> None:
        """
        Test that reset_equipped_tools resets all groups (not incremental).
        
        Bug: In buggy code, calling reset_equipped_tools with one group=True
        would leave previously activated groups still active.
        Fixed: Each call sets absolute final state; groups not explicitly set
        to True are deactivated.
        """
        # Create two tool groups
        self.toolkit.create_tool_group(
            "group1",
            "First test group.",
        )
        self.toolkit.create_tool_group(
            "group2",
            "Second test group.",
        )
        
        # Register a dummy tool in each group
        self.toolkit.register_tool_function(
            dummy_tool,
            group_name="group1",
        )
        # Need to rename second tool to avoid name conflict
        def dummy_tool2() -> ToolResponse:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="dummy2",
                    ),
                ],
            )
        self.toolkit.register_tool_function(
            dummy_tool2,
            group_name="group2",
        )
        
        # Register the meta tool
        self.toolkit.register_tool_function(
            self.toolkit.reset_equipped_tools,
        )
        
        # Activate only group1
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="call1",
                name="reset_equipped_tools",
                input={"group1": True},
            ),
        )
        async for chunk in res:
            # Verify group1 is activated
            self.assertIn("group1", chunk.content[0]["text"])
        
        # Verify only tools from group1 are in schemas
        schemas = self.toolkit.get_json_schemas()
        # Should have meta tool + dummy_tool (from group1)
        self.assertEqual(len(schemas), 2)
        tool_names = {s["function"]["name"] for s in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("dummy_tool", tool_names)
        self.assertNotIn("dummy_tool2", tool_names)
        
        # Now activate only group2 (should deactivate group1)
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="call2",
                name="reset_equipped_tools",
                input={"group2": True},
            ),
        )
        async for chunk in res:
            # Verify group2 is activated
            self.assertIn("group2", chunk.content[0]["text"])
        
        # Verify only tools from group2 are in schemas (group1 should be deactivated)
        schemas = self.toolkit.get_json_schemas()
        # Should have meta tool + dummy_tool2 (from group2)
        self.assertEqual(len(schemas), 2)
        tool_names = {s["function"]["name"] for s in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("dummy_tool2", tool_names)
        self.assertNotIn("dummy_tool", tool_names)

    async def test_reset_equipped_tools_activates_multiple_groups(self) -> None:
        """
        Test that reset_equipped_tools can activate multiple groups at once.
        """
        # Create two tool groups
        self.toolkit.create_tool_group(
            "group_a",
            "Group A.",
        )
        self.toolkit.create_tool_group(
            "group_b",
            "Group B.",
        )
        
        # Register tools in each group (with unique names)
        def tool_a() -> ToolResponse:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="a",
                    ),
                ],
            )
        
        def tool_b() -> ToolResponse:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="b",
                    ),
                ],
            )
        
        self.toolkit.register_tool_function(
            tool_a,
            group_name="group_a",
        )
        self.toolkit.register_tool_function(
            tool_b,
            group_name="group_b",
        )
        
        # Register the meta tool
        self.toolkit.register_tool_function(
            self.toolkit.reset_equipped_tools,
        )
        
        # Activate both groups simultaneously
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="call1",
                name="reset_equipped_tools",
                input={"group_a": True, "group_b": True},
            ),
        )
        async for chunk in res:
            # Verify both groups are mentioned
            text = chunk.content[0]["text"]
            self.assertIn("group_a", text)
            self.assertIn("group_b", text)
        
        # Verify both tools are in schemas
        schemas = self.toolkit.get_json_schemas()
        # Should have meta tool + tool_a + tool_b
        self.assertEqual(len(schemas), 3)
        tool_names = {s["function"]["name"] for s in schemas}
        self.assertIn("reset_equipped_tools", tool_names)
        self.assertIn("tool_a", tool_names)
        self.assertIn("tool_b", tool_names)

    async def test_reset_equipped_tools_with_no_args_deactivates_all(self) -> None:
        """
        Test that reset_equipped_tools with empty input deactivates all groups.
        """
        # Create a tool group and activate it
        self.toolkit.create_tool_group(
            "test_group",
            "Test tool group.",
        )
        self.toolkit.register_tool_function(
            dummy_tool,
            group_name="test_group",
        )
        self.toolkit.register_tool_function(
            self.toolkit.reset_equipped_tools,
        )
        
        # Activate the group
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="call1",
                name="reset_equipped_tools",
                input={"test_group": True},
            ),
        )
        async for chunk in res:
            self.assertIn("test_group", chunk.content[0]["text"])
        
        # Verify tool is accessible
        schemas = self.toolkit.get_json_schemas()
        self.assertEqual(len(schemas), 2)  # meta + dummy_tool
        
        # Now deactivate all groups (empty input)
        res = await self.toolkit.call_tool_function(
            ToolUseBlock(
                type="tool_use",
                id="call2",
                name="reset_equipped_tools",
                input={},
            ),
        )
        async for chunk in res:
            # In buggy code: "Active tool groups successfully: []..."
            # In fixed code: "All tool groups are now deactivated currently."
            text = chunk.content[0]["text"]
            # The fixed code should indicate deactivation
            self.assertTrue(
                "deactivated" in text.lower() or "all tool groups" in text.lower(),
                f"Expected deactivation message, got: {text}"
            )
        
        # Verify only meta tool remains
        schemas = self.toolkit.get_json_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["function"]["name"], "reset_equipped_tools")
