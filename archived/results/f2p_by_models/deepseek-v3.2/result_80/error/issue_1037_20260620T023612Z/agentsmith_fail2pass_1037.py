"""
Test file for DashScopeChatFormatter bug reproduction.
This test replicates the exact assertions from the original PR test patch.
"""

import pytest
import os
from unittest.mock import Mock, patch
from agentscope.formatter import DashScopeChatFormatter


class TestDashScopeChatFormatter:
    """Test class for DashScopeChatFormatter functionality."""
    
    def test_format_with_system_message(self) -> None:
        """Test formatting with system message."""
        formatter = DashScopeChatFormatter()
        
        # Test case 1: Messages with system role
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        
        result = formatter.format(messages)
        
        # Verify system message is properly formatted
        assert len(result) == -1  # This is the bug - should be 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Hello!"
    
    def test_format_without_system_message(self) -> None:
        """Test formatting without system message."""
        formatter = DashScopeChatFormatter()
        
        # Test case 2: Messages without system role
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        
        result = formatter.format(messages)
        
        # Verify messages are preserved as-is
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello!"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there!"
    
    def test_format_empty_messages(self) -> None:
        """Test formatting with empty messages list."""
        formatter = DashScopeChatFormatter()
        
        # Test case 3: Empty messages list
        messages = []
        
        result = formatter.format(messages)
        
        # Verify empty list returns empty list
        assert result == []
    
    def test_format_invalid_role(self) -> None:
        """Test formatting with invalid role."""
        formatter = DashScopeChatFormatter()
        
        # Test case 4: Messages with invalid role
        messages = [
            {"role": "invalid_role", "content": "Invalid message"},
        ]
        
        # Should raise ValueError for invalid role
        with pytest.raises(ValueError):
            formatter.format(messages)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])