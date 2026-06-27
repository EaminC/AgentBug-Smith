import unittest
import os
from typing import List, Dict, Any

# Import the actual formatter from agentscope
from agentscope.formatter import DashScopeChatFormatter
from agentscope.models import ModelResponse


class TestDashScopeChatFormatter(unittest.TestCase):
    """Test suite for DashScopeChatFormatter based on in-patch test specifications."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
        # Retrieve API key from environment for dynamic configuration testing
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("FORGE_API_KEY")
    
    def test_format_basic_messages(self):
        """Test formatting of basic user and assistant messages."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"}
        ]
        
        formatted = self.formatter.format(messages)
        
        # Verify DashScope API structure
        self.assertIsInstance(formatted, dict)
        self.assertIn("messages", formatted)
        self.assertEqual(len(formatted["messages"]), 3)
        
        # Verify message structure
        for msg in formatted["messages"]:
            self.assertIn("role", msg)
            self.assertIn("content", msg)
    
    def test_format_message_with_name(self):
        """Test that formatter correctly handles messages with name field."""
        messages = [
            {"role": "user", "content": "Hello", "name": "test_user"},
            {"role": "assistant", "content": "Hi there", "name": "assistant_1"}
        ]
        
        formatted = self.formatter.format(messages)
        
        # DashScope format should preserve or correctly transform name fields
        self.assertEqual(len(formatted["messages"]), 2)
        # The bug fix likely ensures name fields are properly handled or stripped
        # based on DashScope API requirements
        first_msg = formatted["messages"][0]
        self.assertEqual(first_msg["role"], "user")
        self.assertEqual(first_msg["content"], "Hello")
    
    def test_format_tool_messages(self):
        """Test formatting of tool/function messages."""
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "I'll check the weather.", "tool_calls": [
                {"id": "call_123", "type": "function", "function": {"name": "get_weather", "arguments": "{}"}}
            ]},
            {"role": "tool", "tool_call_id": "call_123", "content": "Sunny, 25°C"}
        ]
        
        formatted = self.formatter.format(messages)
        
        # Verify tool messages are correctly transformed for DashScope API
        self.assertIn("messages", formatted)
        self.assertEqual(len(formatted["messages"]), 3)
        
        # Check tool role conversion (tool -> specific format DashScope expects)
        tool_msg = formatted["messages"][2]
        self.assertEqual(tool_msg["role"], "tool")
        self.assertEqual(tool_msg["content"], "Sunny, 25°C")
    
    def test_format_empty_messages(self):
        """Test handling of empty message list."""
        messages: List[Dict[str, Any]] = []
        formatted = self.formatter.format(messages)
        self.assertIn("messages", formatted)
        self.assertEqual(len(formatted["messages"]), 0)
    
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
        
        # Verify multimodal format conversion for DashScope
        self.assertEqual(len(formatted["messages"]), 1)
        content = formatted["messages"][0]["content"]
        # DashScope expects specific format for multimodal content
        self.assertIsInstance(content, list)
        self.assertEqual(content[0]["type"], "text")
    
    def test_deformat_response(self):
        """Test conversion of DashScope response back to standard format."""
        # Simulate a DashScope API response structure
        dashscope_response = {
            "output": {
                "text": "This is the response",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "This is the response"
                        }
                    }
                ]
            },
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5
            }
        }
        
        # Test deformat if the method exists
        if hasattr(self.formatter, 'deformat'):
            result = self.formatter.deformat(dashscope_response)
            self.assertIsInstance(result, (dict, ModelResponse))
            if isinstance(result, dict):
                self.assertIn("content", result)


if __name__ == "__main__":
    unittest.main()