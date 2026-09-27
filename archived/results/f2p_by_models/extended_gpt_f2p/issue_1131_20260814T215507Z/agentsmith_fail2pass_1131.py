import pytest
from unittest.mock import MagicMock
from strands.tools.registry import ToolRegistry


def test_replace_existing_tool():
    """Test that replacing an existing tool updates the registry correctly."""
    old_tool = MagicMock()
    old_tool.tool_name = "existing_tool"
    old_tool.is_dynamic = False
    old_tool.supports_hot_reload = False

    new_tool = MagicMock()
    new_tool.tool_name = "existing_tool"
    new_tool.is_dynamic = False

    registry = ToolRegistry()
    registry.register_tool(old_tool)
    registry.replace(new_tool)

    assert registry.registry["existing_tool"] == new_tool


def test_replace_nonexistent_tool_raises():
    """Test that replacing a non-existent tool raises ValueError."""
    new_tool = MagicMock()
    new_tool.tool_name = "nonexistent_tool"

    registry = ToolRegistry()

    with pytest.raises(ValueError, match="Cannot replace tool 'nonexistent_tool' - tool does not exist"):
        registry.replace(new_tool)


def test_replace_dynamic_tool_updates_dynamic_tools():
    """Test that replacing a dynamic tool updates both registry and dynamic_tools."""
    old_tool = MagicMock()
    old_tool.tool_name = "dynamic_tool"
    old_tool.is_dynamic = True
    old_tool.supports_hot_reload = True

    new_tool = MagicMock()
    new_tool.tool_name = "dynamic_tool"
    new_tool.is_dynamic = True

    registry = ToolRegistry()
    registry.register_tool(old_tool)
    registry.replace(new_tool)

    assert registry.registry["dynamic_tool"] == new_tool
    assert registry.dynamic_tools["dynamic_tool"] == new_tool


def test_replace_dynamic_with_non_dynamic_removes_from_dynamic_tools():
    """Test replacing a dynamic tool with a non-dynamic tool removes it from dynamic_tools."""
    old_tool = MagicMock()
    old_tool.tool_name = "my_tool"
    old_tool.is_dynamic = True
    old_tool.supports_hot_reload = True

    new_tool = MagicMock()
    new_tool.tool_name = "my_tool"
    new_tool.is_dynamic = False

    registry = ToolRegistry()
    registry.register_tool(old_tool)

    assert "my_tool" in registry.dynamic_tools

    registry.replace(new_tool)

    assert registry.registry["my_tool"] == new_tool
    assert "my_tool" not in registry.dynamic_tools


def test_replace_non_dynamic_with_dynamic_adds_to_dynamic_tools():
    """Test replacing a non-dynamic tool with a dynamic tool adds it to dynamic_tools."""
    old_tool = MagicMock()
    old_tool.tool_name = "my_tool"
    old_tool.is_dynamic = False
    old_tool.supports_hot_reload = False

    new_tool = MagicMock()
    new_tool.tool_name = "my_tool"
    new_tool.is_dynamic = True

    registry = ToolRegistry()
    registry.register_tool(old_tool)

    assert "my_tool" not in registry.dynamic_tools

    registry.replace(new_tool)

    assert registry.registry["my_tool"] == new_tool
    assert registry.dynamic_tools["my_tool"] == new_tool
