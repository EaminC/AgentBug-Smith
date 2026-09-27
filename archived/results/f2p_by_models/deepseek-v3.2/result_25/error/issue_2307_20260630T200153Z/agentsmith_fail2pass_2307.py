import os
import pytest
from unittest.mock import Mock, patch
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test cases for DashScopeChatFormatter."""

    def test_format_without_tools(self) -> None:
        """Test format method without tools."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        formatted = formatter.format(messages)
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        assert formatted == expected

    def test_format_with_tools(self) -> None:
        """Test format method with tools."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "Beijing"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "content": '{"temperature": 22}',
                "tool_call_id": "call_123",
            },
        ]
        formatted = formatter.format(messages)
        expected = [
            {"role": "user", "content": "What's the weather?"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "Beijing"}',
                        },
                    },
                ],
            },
            {
                "role": "tool",
                "content": '{"temperature": 22}',
                "tool_call_id": "call_123",
            },
        ]
        assert formatted == expected

    def test_format_with_tools_and_name(self) -> None:
        """Test format method with tools and name field."""
        formatter = DashScopeChatFormatter()
        messages = [
            {"role": "user", "content": "Hello", "name": "Alice"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test"}',
                        },
                    },
                ],
            },
        ]
        formatted = formatter.format(messages)
        expected = [
            {"role": "user", "content": "Hello", "name": "Alice"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search",
                            "arguments": '{"query": "test"}',
                        },
                    },
                ],
            },
        ]
        assert formatted == expected

    def test_format_empty_messages(self) -> None:
        """Test format method with empty messages list."""
        formatter = DashScopeChatFormatter()
        messages = []
        formatted = formatter.format(messages)
        assert formatted == []

    def test_format_invalid_role(self) -> None:
        """Test format method with invalid role."""
        formatter = DashScopeChatFormatter()
        messages = [{"role": "invalid", "content": "test"}]
        # Should raise ValueError or handle gracefully depending on implementation
        with pytest.raises(ValueError):
            formatter.format(messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])