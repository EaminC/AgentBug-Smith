# tests/formatter_dashscope_test.py
import pytest
import os
from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import Msg


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter bug reproduction.
    
    Tests the formatting of AgentScope messages to DashScope API format.
    This reproduces issues with multimodal content handling and role mapping.
    """
    
    def setup_method(self):
        """Initialize formatter before each test."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_chat_basic_text(self):
        """Test formatting of simple text messages."""
        messages = [
            Msg(name="user", role="user", content="Hello, assistant!")
        ]
        
        result = self.formatter.format_chat(messages)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello, assistant!"
    
    def test_format_chat_system_message(self):
        """Test that system messages are correctly formatted without name field issues."""
        messages = [
            Msg(name="system", role="system", content="You are a helpful assistant."),
            Msg(name="user", role="user", content="Hi")
        ]
        
        result = self.formatter.format_chat(messages)
        
        # System message should be first with correct role
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."
        # Should not contain 'name' key if not supported by DashScope format
        assert "name" not in result[0]
        
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hi"
    
    def test_format_chat_multimodal_content(self):
        """Test formatting of multimodal messages (text + image).
        
        This reproduces the bug where multimodal content lists are incorrectly
        stringified or have incorrect structure for DashScope API.
        """
        messages = [
            Msg(
                name="user",
                role="user",
                content=[
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
                ]
            )
        ]
        
        result = self.formatter.format_chat(messages)
        
        # Content should remain a list for multimodal
        assert isinstance(result[0]["content"], list)
        assert len(result[0]["content"]) == 2
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][1]["type"] == "image_url"
        assert result[0]["content"][1]["image_url"]["url"] == "https://example.com/image.jpg"
    
    def test_format_chat_assistant_response(self):
        """Test formatting of assistant responses."""
        messages = [
            Msg(name="user", role="user", content="Hello"),
            Msg(name="assistant", role="assistant", content="Hello! How can I help?")
        ]
        
        result = self.formatter.format_chat(messages)
        
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hello! How can I help?"
        # Verify no name leakage in assistant message
        assert "name" not in result[1]
    
    def test_format_chat_empty_content_handling(self):
        """Test handling of empty or None content."""
        messages = [
            Msg(name="user", role="user", content="")
        ]
        
        result = self.formatter.format_chat(messages)
        
        assert result[0]["content"] == ""
    
    def test_format_chat_complex_conversation(self):
        """Test formatting of a complex multi-turn conversation."""
        messages = [
            Msg(name="system", role="system", content="Be concise."),
            Msg(name="user1", role="user", content="Question 1"),
            Msg(name="assistant", role="assistant", content="Answer 1"),
            Msg(name="user1", role="user", content="Question 2")
        ]
        
        result = self.formatter.format_chat(messages)
        
        assert len(result) == 4
        assert result[0]["role"] == "system"
        assert result[1]["role"] == "user"
        assert result[2]["role"] == "assistant"
        assert result[3]["role"] == "user"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])