import pytest
import strands
from strands import ToolContext


def test_tool_context_param_name_mismatch_default():
    # Using context=True means the ToolContext param must be named "tool_context"
    with pytest.raises(ValueError, match=r"param_name=<context> | ToolContext param must be named 'tool_context'"):

        @strands.tool(context=True)
        def tool_func(context: ToolContext):
            return {"ok": True}


def test_tool_context_param_name_mismatch_custom_name():
    # Using context="my_context" means the ToolContext param must be named "my_context"
    with pytest.raises(ValueError, match=r"param_name=<tool_context> | ToolContext param must be named 'my_context'"):

        @strands.tool(context="my_context")
        def tool_func(tool_context: ToolContext):
            return {"ok": True}


def test_tool_context_param_missing_context_flag():
    # If a ToolContext param is present but context flag is not set, error is raised
    with pytest.raises(ValueError, match=r"@tool\(context\) must be set if passing in ToolContext param"):

        @strands.tool
        def tool_func(tool_context: ToolContext):
            return {"ok": True}
