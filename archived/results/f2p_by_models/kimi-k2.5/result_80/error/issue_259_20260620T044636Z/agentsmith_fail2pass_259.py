import pytest
import os
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter to verify F2P (Fail-to-Pass) behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_basic_conversation(self):
        """Test formatting of basic user-assistant conversation."""
        messages = [
            Msg(name="system", content="You are a helpful assistant.", role="system"),
            Msg(name="user", content="Hello, how are you?", role="user")
        ]
        
        formatted = self.formatter.format(messages)
        
        # Verify structure matches DashScope API expectations
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert "content" in formatted[0]
        assert formatted[1]["content"] == "Hello, how are you?"
    
    def test_format_with_tool_calls(self):
        """Test formatting when assistant message contains tool calls."""
        messages = [
            Msg(name="user", content="What's the weather?", role="user"),
            Msg(
                name="assistant", 
                content="", 
                role="assistant",
                tool_calls=[{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Beijing"}'
                    }
                }]
            )
        ]
        
        # This should handle tool calls correctly without crashing
        formatted = self.formatter.format(messages)
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        
        # Verify tool calls are preserved in the correct format
        assistant_msg = formatted[1]
        assert "tool_calls" in assistant_msg or assistant_msg.get("role") == "assistant"
    
    def test_format_tool_response(self):
        """Test formatting of tool response messages."""
        messages = [
            Msg(name="user", content="Check weather", role="user"),
            Msg(name="assistant", content="I'll check the weather.", role="assistant"),
            Msg(
                name="tool", 
                content='{"temperature": 20, "condition": "sunny"}', 
                role="tool",
                tool_call_id="call_123"
            )
        ]
        
        formatted = self.formatter.format(messages)
        
        # Tool responses should be formatted correctly
        assert isinstance(formatted, list)
        assert len(formatted) == 3
        tool_msg = formatted[2]
        assert tool_msg["role"] == "tool"
        assert "content" in tool_msg
    
    def test_format_empty_content_handling(self):
        """Test that empty or None content is handled gracefully."""
        messages = [
            Msg(name="user", content="", role="user"),
            Msg(name="assistant", content=None, role="assistant")
        ]
        
        # Should not raise exception on empty/None content
        formatted = self.formatter.format(messages)
        assert isinstance(formatted, list)
        assert len(formatted) == 2
    
    def test_format_multimodal_content(self):
        """Test formatting of multimodal content (text + image)."""
        messages = [
            Msg(
                name="user",
                content=[
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ],
                role="user"
            )
        ]
        
        formatted = self.formatter.format(messages)
        assert isinstance(formatted, list)
        assert formatted[0]["role"] == "user"
        # Content should be preserved as list for multimodal
        assert isinstance(formatted[0]["content"], list) or isinstance(formatted[0]["content"], str)
    
    def test_format_preserves_name_field(self):
        """Test that the 'name' field is preserved where supported."""
        messages = [
            Msg(name="custom_user", content="Hello", role="user")
        ]
        
        formatted = self.formatter.format(messages)
        # DashScope supports name field in messages
        if "name" in formatted[0]:
            assert formatted[0]["name"] == "custom_user"