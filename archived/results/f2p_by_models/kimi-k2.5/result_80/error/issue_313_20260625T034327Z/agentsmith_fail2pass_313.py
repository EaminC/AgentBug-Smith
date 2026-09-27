import pytest
import os
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg


class TestDashScopeChatFormatter:
    """Tests for DashScopeChatFormatter to verify proper message formatting."""
    
    def setup_method(self):
        """Initialize formatter before each test."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_system_message_handling(self):
        """
        Test that system messages are properly formatted or handled.
        This addresses bugs where system messages might be incorrectly
        formatted or omitted in DashScope API calls.
        """
        messages = [
            Msg(name="system", content="You are a helpful assistant", role="system"),
            Msg(name="user", content="Hello", role="user")
        ]
        
        formatted = self.formatter.format(messages)
        
        # Verify the output is a list of dictionaries with correct roles
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        
        # Verify system message is preserved correctly
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant"
        
        # Verify user message follows
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "Hello"
    
    def test_format_multi_turn_conversation(self):
        """Test formatting of multi-turn conversations."""
        messages = [
            Msg(name="user", content="Hello", role="user"),
            Msg(name="assistant", content="Hi there!", role="assistant"),
            Msg(name="user", content="How are you?", role="user")
        ]
        
        formatted = self.formatter.format(messages)
        
        assert len(formatted) == 3
        assert formatted[0]["role"] == "user"
        assert formatted[1]["role"] == "assistant"
        assert formatted[2]["role"] == "user"
    
    def test_format_empty_content_handling(self):
        """Test that empty content is handled properly without errors."""
        messages = [
            Msg(name="assistant", content="", role="assistant")
        ]
        
        # Should not raise an exception
        formatted = self.formatter.format(messages)
        assert isinstance(formatted, list)
        assert len(formatted) == 1
        assert formatted[0]["content"] == ""
    
    def test_format_tool_message_handling(self):
        """Test formatting of tool/function messages if applicable."""
        messages = [
            Msg(name="user", content="Call tool", role="user"),
            Msg(name="assistant", content="Calling tool", role="assistant", 
                tool_calls=[{"id": "123", "function": {"name": "test", "arguments": "{}"}}]),
            Msg(name="tool", content="Result", role="tool", tool_call_id="123")
        ]
        
        formatted = self.formatter.format(messages)
        
        # Verify tool messages are properly formatted
        assert isinstance(formatted, list)
        assert len(formatted) == 3
    
    def test_format_with_name_field(self):
        """Test that name fields are preserved or stripped appropriately."""
        messages = [
            Msg(name="custom_user", content="Hello", role="user")
        ]
        
        formatted = self.formatter.format(messages)
        
        # DashScope format should handle the message correctly
        assert formatted[0]["role"] == "user"
        assert "content" in formatted[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])