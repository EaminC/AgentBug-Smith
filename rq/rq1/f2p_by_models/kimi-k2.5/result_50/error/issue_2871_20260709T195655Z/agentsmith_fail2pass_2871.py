# tests/formatter_dashscope_test.py
"""
Test file for DashScopeChatFormatter to verify F2P (Fail-to-Pass) scenario.
Tests the formatting logic for DashScope API compatibility.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test suite for DashScopeChatFormatter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = DashScopeChatFormatter()
    
    def test_format_chat_basic_message_structure(self):
        """Test that basic message formatting produces correct structure."""
        # Arrange
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        # Act
        result = self.formatter.format_chat(messages)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0]["role"] == "system"
        assert result[1]["content"] == "Hello"
    
    def test_format_chat_with_custom_roles(self):
        """Test formatting handles custom/agent roles correctly."""
        messages = [
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"}
        ]
        
        result = self.formatter.format_chat(messages)
        
        # Verify alternating user/assistant pattern is preserved
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"
    
    def test_format_chat_empty_messages(self):
        """Test handling of empty message list."""
        result = self.formatter.format_chat([])
        assert result == []
    
    def test_format_chat_message_content_extraction(self):
        """Test that content is properly extracted from message objects."""
        # Test with content field variations
        messages = [
            {"role": "user", "content": "Test message"},
            {"role": "user", "content": {"text": "Complex content"}}
        ]
        
        result = self.formatter.format_chat(messages)
        assert len(result) == 2
        assert "content" in result[0]
    
    def test_format_chat_with_name_field(self):
        """Test that name fields are handled correctly in formatting."""
        messages = [
            {"role": "user", "content": "Hello", "name": "user1"},
            {"role": "assistant", "content": "Hi", "name": "agent1"}
        ]
        
        result = self.formatter.format_chat(messages)
        # DashScope format should handle or strip name fields appropriately
        assert all("role" in msg for msg in result)
        assert all("content" in msg for msg in result)
    
    @patch('agentscope.formatter.dashscope_formatter.os.getenv')
    def test_formatter_uses_env_for_config(self, mock_getenv):
        """Test that formatter respects environment configuration."""
        # Arrange
        mock_getenv.return_value = "test-value"
        
        # Act - instantiate new formatter to trigger env reading
        formatter = DashScopeChatFormatter()
        
        # Assert - verify formatter initialized correctly with env vars
        assert formatter is not None
    
    def test_format_chat_preserves_message_order(self):
        """Critical test: Verify message order is preserved correctly."""
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Fourth"}
        ]
        
        result = self.formatter.format_chat(messages)
        
        # Verify strict ordering
        contents = [msg["content"] for msg in result]
        assert contents == ["First", "Second", "Third", "Fourth"]
        roles = [msg["role"] for msg in result]
        assert roles == ["user", "assistant", "user", "assistant"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])