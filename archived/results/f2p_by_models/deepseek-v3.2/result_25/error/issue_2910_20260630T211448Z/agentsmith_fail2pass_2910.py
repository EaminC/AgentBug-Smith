import os
import pytest
from unittest.mock import patch, MagicMock
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test class for DashScopeChatFormatter based on in-patch tests."""

    def test_format_with_system_prompt(self) -> None:
        """Test formatting with system prompt."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        
        result = formatter.format(messages)
        
        expected = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        assert result == expected

    def test_format_without_system_prompt(self) -> None:
        """Test formatting without system prompt."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        
        result = formatter.format(messages)
        
        expected = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert result == expected

    def test_format_with_tool_calls(self) -> None:
        """Test formatting with tool calls."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "What's the weather?"},
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
        ]
        
        result = formatter.format(messages)
        
        expected = [
            {"role": "user", "content": "What's the weather?"},
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
        ]
        assert result == expected

    def test_format_with_tool_responses(self) -> None:
        """Test formatting with tool responses."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "What's the weather?"},
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
                "content": "Sunny, 22°C",
                "tool_call_id": "call_123",
                "name": "get_weather"
            },
        ]
        
        result = formatter.format(messages)
        
        expected = [
            {"role": "user", "content": "What's the weather?"},
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
                "content": "Sunny, 22°C",
                "tool_call_id": "call_123",
                "name": "get_weather"
            },
        ]
        assert result == expected

    def test_format_empty_messages(self) -> None:
        """Test formatting with empty messages list."""
        formatter = DashScopeChatFormatter()
        messages = []
        
        result = formatter.format(messages)
        
        assert result == []

    def test_format_invalid_role(self) -> None:
        """Test formatting with invalid role should raise error."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "invalid_role", "content": "test"},
        ]
        
        with pytest.raises(ValueError):
            formatter.format(messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])