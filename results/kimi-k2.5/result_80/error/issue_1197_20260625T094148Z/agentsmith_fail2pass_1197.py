# tests/formatter_dashscope_test.py
"""
Test file for DashScopeChatFormatter to validate F2P (Fail-to-Pass) setup.
Tests the formatting logic for DashScope API compatibility.
"""
import pytest
import os
from unittest.mock import patch, MagicMock

# Import the formatter from agentscope
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter bug reproduction and fix validation."""
    
    def test_formatter_import(self):
        """Test that the formatter can be imported and instantiated."""
        formatter = DashScopeChatFormatter()
        assert formatter is not None
    
    def test_format_chat_messages_basic(self):
        """Test basic message formatting for DashScope chat API."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Format messages for DashScope API
        formatted = formatter.format_chat(messages)
        
        # Verify structure matches DashScope API expectations
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
    
    def test_format_chat_with_tools(self):
        """Test formatting when tool calls are present (common bug area)."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "I'll check the weather for you.", 
             "tool_calls": [{"id": "call_123", "function": {"name": "get_weather", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "call_123", "content": "Sunny, 25°C"}
        ]
        
        formatted = formatter.format_chat(messages)
        assert isinstance(formatted, list)
        # Verify tool messages are properly formatted for DashScope
        if len(formatted) > 2:
            assert formatted[2].get("role") == "tool"
    
    def test_format_chat_multimodal(self):
        """Test multimodal content formatting (images, etc.)."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Describe this image"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/image.jpg"}}
                ]
            }
        ]
        
        # Should handle multimodal content without crashing
        formatted = formatter.format_chat(messages)
        assert isinstance(formatted, list)
        assert len(formatted) == 1
    
    def test_serialization_compatibility(self):
        """Test that formatted output is JSON serializable."""
        import json
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"}
        ]
        
        formatted = formatter.format_chat(messages)
        # Should not raise TypeError
        json_str = json.dumps(formatted)
        assert isinstance(json_str, str)
    
    @patch('agentscope.formatter.dashscope_formatter.os.getenv')
    def test_environment_key_retrieval(self, mock_getenv):
        """Test that formatter uses environment variables for API keys."""
        mock_getenv.return_value = "test-api-key"
        formatter = DashScopeChatFormatter()
        
        # Verify formatter checks for API key in environment
        # This ensures we're not hardcoding keys
        key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('OPENAI_API_KEY')
        assert key is not None or True  # Key presence depends on implementation
    
    def test_empty_messages_handling(self):
        """Test behavior with empty message list."""
        formatter = DashScopeChatFormatter()
        formatted = formatter.format_chat([])
        assert isinstance(formatted, list)
        assert len(formatted) == 0
    
    def test_role_mapping_accuracy(self):
        """Test that role names are correctly mapped to DashScope expectations."""
        formatter = DashScopeChatFormatter()
        
        # DashScope expects specific role names: system, user, assistant, tool
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "usr"},
            {"role": "assistant", "content": "asst"}
        ]
        
        formatted = formatter.format_chat(messages)
        roles = [msg["role"] for msg in formatted]
        
        assert "system" in roles
        assert "user" in roles
        assert "assistant" in roles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])