import pytest

from strands.tools.registry import ToolRegistry


def test_validate_tool_spec_with_anyof_property():
    """Test that validate_tool_spec does not add type: 'string' to anyOf properties.

    This is important for MCP tools that use anyOf for optional/union types like
    Optional[List[str]]. Adding type: 'string' causes models to return string-encoded
    JSON instead of proper arrays/objects.
    """
    tool_spec = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "regular_field": {},  # Should get type: "string"
                    "anyof_field": {
                        "anyOf": [
                            {"type": "array", "items": {"type": "string"}},
                            {"type": "null"},
                        ]
                    },
                },
            }
        },
    }

    registry = ToolRegistry()
    registry.validate_tool_spec(tool_spec)

    props = tool_spec["inputSchema"]["json"]["properties"]

    # Regular field should get default type: "string"
    assert props["regular_field"]["type"] == "string"
    assert props["regular_field"]["description"] == "Property regular_field"

    # anyOf field should NOT get type: "string" added
    assert "type" not in props["anyof_field"], "anyOf property should not have type added"
    assert "anyOf" in props["anyof_field"], "anyOf should be preserved"
    assert props["anyof_field"]["description"] == "Property anyof_field"


def test_validate_tool_spec_with_composition_keywords():
    """Test that validate_tool_spec does not add type: 'string' to composition keyword properties.

    JSON Schema composition keywords (anyOf, oneOf, allOf, not) define type constraints.
    Properties using these should not get a default type added.
    """
    tool_spec = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "regular_field": {},  # Should get type: "string"
                    "oneof_field": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ]
                    },
                    "allof_field": {
                        "allOf": [
                            {"minimum": 0},
                            {"maximum": 100},
                        ]
                    },
                    "not_field": {"not": {"type": "null"}},
                },
            }
        },
    }

    registry = ToolRegistry()
    registry.validate_tool_spec(tool_spec)

    props = tool_spec["inputSchema"]["json"]["properties"]

    # Regular field should get default type: "string"
    assert props["regular_field"]["type"] == "string"

    # Composition keyword fields should NOT get type: "string" added
    assert "type" not in props["oneof_field"], "oneOf property should not have type added"
    assert "oneOf" in props["oneof_field"], "oneOf should be preserved"

    assert "type" not in props["allof_field"], "allOf property should not have type added"
    assert "allOf" in props["allof_field"], "allOf should be preserved"

    assert "type" not in props["not_field"], "not property should not have type added"
    assert "not" in props["not_field"], "not should be preserved"

    # All should have descriptions
    for field in ["oneof_field", "allof_field", "not_field"]:
        assert props[field]["description"] == f"Property {field}"


def test_validate_tool_spec_with_ref_property():
    """Test that validate_tool_spec does not modify $ref properties."""
    tool_spec = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "ref_field": {"$ref": "#/$defs/SomeType"},
                },
            }
        },
    }

    registry = ToolRegistry()
    registry.validate_tool_spec(tool_spec)

    props = tool_spec["inputSchema"]["json"]["properties"]

    # $ref field should not be modified
    assert props["ref_field"] == {"$ref": "#/$defs/SomeType"}
    assert "type" not in props["ref_field"]
    assert "description" not in props["ref_field"]
