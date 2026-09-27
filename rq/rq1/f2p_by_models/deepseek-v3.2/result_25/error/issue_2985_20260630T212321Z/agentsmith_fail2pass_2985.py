import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from crewai.agents.formatters.dashscope_formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter based on the PR's unit tests."""
    
    def test_format_messages_with_system_message(self):
        """Test formatting messages with a system message."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        result = formatter.format_messages(messages)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello!"
    
    def test_format_messages_without_system_message(self):
        """Test formatting messages without a system message."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        result = formatter.format_messages(messages)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello!"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there!"
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "How are you?"
    
    def test_format_messages_with_tool_calls(self):
        """Test formatting messages with tool calls."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "user", "content": "What's the weather in London?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "London"}'
                        }
                    }
                ]
            },
            {
                "role": "tool",
                "content": '{"temperature": 15, "condition": "cloudy"}',
                "tool_call_id": "call_123"
            }
        ]
        
        result = formatter.format_messages(messages)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "What's the weather in London?"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] is None
        assert "tool_calls" in result[1]
        assert result[2]["role"] == "tool"
        assert result[2]["content"] == '{"temperature": 15, "condition": "cloudy"}'
        assert result[2]["tool_call_id"] == "call_123"
    
    def test_format_messages_empty_list(self):
        """Test formatting an empty message list."""
        formatter = DashScopeChatFormatter()
        
        result = formatter.format_messages([])
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_format_messages_invalid_role(self):
        """Test formatting messages with an invalid role."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "invalid_role", "content": "This should not break"}
        ]
        
        # The formatter should handle invalid roles gracefully
        result = formatter.format_messages(messages)
        
        assert isinstance(result, list)
        assert len(result) == 1
        # The formatter might preserve the role or convert it
        # This test ensures it doesn't crash
    
    @pytest.mark.asyncio
    async def test_format_messages_async_context(self):
        """Test formatting messages in async context."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            {"role": "system", "content": "Async test"},
            {"role": "user", "content": "Async message"}
        ]
        
        result = formatter.format_messages(messages)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "Async test"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Async message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])