# tests/formatter_dashscope_test.py
import pytest
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter to verify F2P bug fix."""
    
    def test_format_basic_messages(self):
        """Test basic message formatting for DashScope API."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            Msg(name="user", content="Hello", role="user"),
            Msg(name="assistant", content="Hi there!", role="assistant")
        ]
        
        formatted = formatter.format(messages)
        
        assert isinstance(formatted, list)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"
        assert formatted[1]["role"] == "assistant"
        assert formatted[1]["content"] == "Hi there!"
    
    def test_format_system_message(self):
        """
        Test that system messages are correctly formatted.
        
        This test addresses the bug where system messages were not properly
        converted to DashScope's expected format or were being dropped.
        """
        formatter = DashScopeChatFormatter()
        
        messages = [
            Msg(name="system", content="You are a helpful assistant.", role="system"),
            Msg(name="user", content="Hello", role="user")
        ]
        
        formatted = formatter.format(messages)
        
        # System message should be preserved and correctly formatted
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "You are a helpful assistant."
        assert formatted[1]["role"] == "user"
    
    def test_format_multi_turn_conversation(self):
        """Test formatting of multi-turn conversations."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            Msg(name="system", content="Be concise.", role="system"),
            Msg(name="user", content="What is 2+2?", role="user"),
            Msg(name="assistant", content="4", role="assistant"),
            Msg(name="user", content="What about 3+3?", role="user")
        ]
        
        formatted = formatter.format(messages)
        
        assert len(formatted) == 4
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "What is 2+2?"
        assert formatted[2]["role"] == "assistant"
        assert formatted[2]["content"] == "4"
        assert formatted[3]["role"] == "user"
        assert formatted[3]["content"] == "What about 3+3?"
    
    def test_format_empty_content(self):
        """Test handling of messages with empty content."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            Msg(name="user", content="", role="user")
        ]
        
        formatted = formatter.format(messages)
        
        assert len(formatted) == 1
        assert formatted[0]["content"] == ""
    
    def test_format_message_with_name(self):
        """Test that message names are handled correctly in the format."""
        formatter = DashScopeChatFormatter()
        
        messages = [
            Msg(name="user123", content="Hello", role="user")
        ]
        
        formatted = formatter.format(messages)
        
        # DashScope format may or may not include name depending on the fix
        # but role and content must be present
        assert "role" in formatted[0]
        assert "content" in formatted[0]
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"