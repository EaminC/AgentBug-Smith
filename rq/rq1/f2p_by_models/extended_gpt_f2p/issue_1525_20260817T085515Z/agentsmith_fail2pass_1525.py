from strands import tool
from enum import Enum


def test_tool_nullable_required_field_preserves_anyof():
    """Test that a required nullable field preserves anyOf so the model can pass null.

    Regression test for https://github.com/strands-agents/sdk-python/issues/1525
    """

    class Priority(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    @tool
    def prioritized_task(description: str, priority: Priority | None) -> str:
        """Create a task with optional priority.

        Args:
            description: Task description
            priority: Optional priority level
        """
        return f"{description}: {priority}"

    spec = prioritized_task.tool_spec
    schema = spec["inputSchema"]["json"]

    expected_schema = {
        "$defs": {
            "Priority": {
                "enum": ["high", "medium", "low"],
                "title": "Priority",
                "type": "string",
            },
        },
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Task description",
            },
            "priority": {
                "anyOf": [
                    {"$ref": "#/$defs/Priority"},
                    {"type": "null"},
                ],
                "description": "Optional priority level",
            },
        },
        "required": ["description", "priority"],
    }

    assert schema == expected_schema


def test_tool_nullable_optional_field_simplifies_anyof():
    """Test that a non-required nullable field still gets anyOf simplified."""

    @tool
    def my_tool(name: str, tag: str | None = None) -> str:
        """A tool.

        Args:
            name: The name
            tag: An optional tag
        """
        return f"{name}: {tag}"

    spec = my_tool.tool_spec
    schema = spec["inputSchema"]["json"]

    # tag has a default, so it should NOT be required
    assert "name" in schema["required"]
    assert "tag" not in schema["required"]

    # Since tag is not required, anyOf should be simplified away
    assert "anyOf" not in schema["properties"]["tag"]
    assert schema["properties"]["tag"]["type"] == "string"
