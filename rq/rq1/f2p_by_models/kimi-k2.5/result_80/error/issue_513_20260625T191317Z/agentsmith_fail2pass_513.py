"""
Test file for DashScope formatter bug reproduction.
Tests the format method of DashScopeChatFormatter to ensure proper message formatting.
"""
import pytest
import os
from unittest.mock import patch, MagicMock

# Import the actual formatter class from the repository
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter formatting logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_basic_conversation(self):
        """Test formatting of basic conversation messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
        ]
        
        # Format should convert messages to DashScope-compatible format
        formatted = self.formatter.format(messages)
        
        # Assert that the formatted output has the expected structure
        assert isinstance(formatted, list)
        assert len(formatted) == 3
        
        # Verify system message handling (common bug area)
        system_msg = formatted[0]
        assert system_msg.get("role") == "system"
        assert "content" in system_msg
    
    def test_format_multimodal_content(self):
        """Test formatting of multimodal content (text + image)."""
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ]
            }
        ]
        
        formatted = self.formatter.format(messages)
        
        # Should handle complex content structures without error
        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
    
    def test_format_empty_messages(self):
        """Test handling of empty message list."""
        formatted = self.formatter.format([])
        assert formatted == []
    
    def test_format_role_mapping(self):
        """Test that roles are correctly mapped to DashScope expected values."""
        messages = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]
        
        formatted = self.formatter.format(messages)
        
        # DashScope typically uses 'user', 'assistant', 'system'
        roles = [msg.get("role") for msg in formatted]
        assert "user" in roles
        assert "assistant" in roles
    
    def test_format_with_tools(self):
        """Test formatting when tool/function calling is involved."""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "Let me check.", "tool_calls": [{"id": "call_1", "function": {"name": "get_weather", "arguments": "{}"}}]},
            {"role": "tool", "content": "Sunny, 25°C", "tool_call_id": "call_1"}
        ]
        
        # Should handle tool-related fields without stripping them incorrectly
        formatted = self.formatter.format(messages)
        assert len(formatted) == 3
        
        # Verify tool role preservation
        tool_msg = formatted[2]
        assert tool_msg.get("role") == "tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])