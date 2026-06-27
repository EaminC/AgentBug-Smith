import pytest
import os
from unittest.mock import Mock, patch
from agentscope.formatter import DashScopeChatFormatter

class TestDashScopeChatFormatter:
    """Tests for DashScopeChatFormatter bug reproduction and verification."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_messages_with_tool_calls(self):
        """
        Test that formatter correctly handles messages with tool calls.
        This reproduces the bug where tool call formatting failed.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's the weather in Beijing?"},
            {
                "role": "assistant", 
                "content": "I'll check the weather for you.",
                "tool_calls": [
                    {
                        "id": "call_123", 
                        "type": "function", 
                        "function": {
                            "name": "get_weather", 
                            "arguments": '{"location": "Beijing"}'
                        }
                    }
                ]
            },
            {
                "role": "tool",
                "content": '{"temperature": "20°C", "condition": "Sunny"}',
                "tool_call_id": "call_123"
            }
        ]
        
        # This should not raise an exception after the fix
        formatted = self.formatter.format(messages)
        
        # Validate structure
        assert isinstance(formatted, list)
        assert len(formatted) == len(messages)
        
        # Validate tool call formatting
        assistant_msg = formatted[2]
        assert "tool_calls" in assistant_msg or "toolCalls" in assistant_msg
        
    def test_format_response_parsing(self):
        """
        Test parsing of DashScope API responses.
        Bug: Response parsing failed when content was None or missing.
        """
        # Mock response that triggered the bug (missing content field)
        mock_response = {
            "output": {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": "{}"
                                    }
                                }
                            ]
                            # Note: missing 'content' field - this caused the bug
                        }
                    }
                ]
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5
            }
        }
        
        # Should handle missing content gracefully
        result = self.formatter.format_response(mock_response)
        assert result is not None
        
    def test_format_empty_content_handling(self):
        """
        Test that empty or None content is handled correctly.
        Bug: Formatter crashed when content was None.
        """
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": None},  # This triggered the bug
            {"role": "assistant", "content": "Follow up"}
        ]
        
        # Should not raise TypeError or AttributeError
        formatted = self.formatter.format(messages)
        assert isinstance(formatted, list)
        
    def test_format_multimodal_content(self):
        """
        Test formatting of multimodal content (text + images).
        Bug: Image URLs were not properly formatted for DashScope API.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://example.com/image.jpg"
                        }
                    }
                ]
            }
        ]
        
        formatted = self.formatter.format(messages)
        assert len(formatted) == 1
        user_msg = formatted[0]
        
        # Verify multimodal structure is preserved for DashScope
        assert "content" in user_msg
        assert isinstance(user_msg["content"], list)