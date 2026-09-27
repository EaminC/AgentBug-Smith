import pytest
from unittest.mock import patch

from agentscope.models.openai_model import OpenAIChatWrapper


def test_single_dict_message_raises_list_type_error():
    """
    Test that passing a single dict (instead of a list) to OpenAIChatWrapper
    raises a ValueError clearly indicating that a list is expected.
    
    Regression test for issue #71: Previously, passing a single dict would
    incorrectly raise "Each message in the 'messages' list must contain..."
    because the code iterated over dict keys. After the fix, it should raise
    "OpenAI `messages` field expected type `list`...".
    """
    # Patch __init__ to avoid requiring real API keys/environment
    with patch.object(OpenAIChatWrapper, "__init__", return_value=None):
        wrapper = OpenAIChatWrapper.__new__(OpenAIChatWrapper)
        wrapper.model_name = "gpt-3.5-turbo"
        wrapper.generate_args = {}
        
        # A single message dict (not wrapped in a list) - the problematic input
        single_message = {"role": "user", "content": "Hello, this is a test"}
        
        with pytest.raises(ValueError) as exc_info:
            wrapper(single_message)
        
        # The fix adds a specific type check with this message
        error_message = str(exc_info.value)
        assert "expected type `list`" in error_message, (
            f"Expected error message to indicate 'list' type is required, "
            f"but got: {error_message}"
        )
