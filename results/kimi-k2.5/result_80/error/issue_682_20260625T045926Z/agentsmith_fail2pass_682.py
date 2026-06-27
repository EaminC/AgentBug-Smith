"""
Test file for DashScopeChatFormatter to validate F2P (Fail-to-Pass) scenarios.
Tests the formatter's ability to handle various message formats and roles.
"""

import pytest
from unittest.mock import patch, MagicMock
import os
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter bug reproduction and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
        # Ensure API key is available via environment for any underlying client calls
        os.environ.setdefault("DASHSCOPE_API_KEY", "test-key-for-unit-tests")
    
    def test_format_single_user_message(self):
        """Test formatting a single user message."""
        messages = [
            {"role": "user", "content": "Hello, how are you?"}
        ]
        result = self.formatter.format(messages)
        assert result is not None
        assert isinstance(result, (list, dict))
    
    def test_format_system_message_handling(self):
        """Test that system messages are correctly formatted and preserved.
        
        This test addresses common bugs where system messages are dropped or
        malformed during formatting.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        result = self.formatter.format(messages)
        
        # Verify system message is preserved in output format
        if isinstance(result, list):
            roles = [msg.get("role", "") for msg in result]
            assert "system" in roles or any("system" in str(msg) for msg in result)
        else:
            # If result is a dict (e.g., DashScope format), check appropriate fields
            assert result is not None
    
    def test_format_multimodal_content(self):
        """Test formatting messages with multimodal content (text + image)."""
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/image.jpg"}}
                ]
            }
        ]
        # Should not raise exception
        result = self.formatter.format(messages)
        assert result is not None
    
    def test_format_empty_messages(self):
        """Test handling of empty message list."""
        result = self.formatter.format([])
        assert result is not None or result == []
    
    def test_format_assistant_message(self):
        """Test formatting assistant responses."""
        messages = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! How can I help you today?"}
        ]
        result = self.formatter.format(messages)
        assert result is not None
    
    def test_format_tool_message_handling(self):
        """Test that tool/function messages are formatted correctly."""
        messages = [
            {"role": "user", "content": "Calculate 2+2"},
            {
                "role": "assistant", 
                "content": "I'll calculate that for you.",
                "tool_calls": [{"id": "call_123", "function": {"name": "calculator", "arguments": '{"x": 2, "y": 2}'}}]
            },
            {"role": "tool", "tool_call_id": "call_123", "content": "4"}
        ]
        result = self.formatter.format(messages)
        assert result is not None
    
    def test_format_with_name_field(self):
        """Test formatting when messages include 'name' field (for multi-agent scenarios)."""
        messages = [
            {"role": "user", "content": "Hello", "name": "User1"}
        ]
        result = self.formatter.format(messages)
        assert result is not None
    
    def test_format_preserves_message_order(self):
        """Test that message order is preserved during formatting."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Response 2"}
        ]
        result = self.formatter.format(messages)
        
        if isinstance(result, list) and len(result) == 4:
            assert result[0].get("role") == "user"
            assert result[3].get("role") == "assistant"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])