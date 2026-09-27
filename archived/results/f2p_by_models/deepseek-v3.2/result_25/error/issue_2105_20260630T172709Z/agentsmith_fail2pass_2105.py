"""
Test for DashScopeChatFormatter bug fix.
This test replicates the unit test from the original PR patch.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from agentscope.formatter import DashScopeChatFormatter


def test_dashscope_chat_formatter_without_system():
    """Test DashScopeChatFormatter when system message is not provided."""
    # Initialize formatter with API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    formatter = DashScopeChatFormatter(api_key=api_key)
    
    # Create test messages without system message
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    # Format the messages
    formatted = formatter.format(messages)
    
    # Assertions from original test
    assert isinstance(formatted, dict)
    assert "input" in formatted
    assert "parameters" in formatted
    
    # Check that messages are properly formatted
    assert len(formatted["input"]["messages"]) == 3
    assert formatted["input"]["messages"][0]["role"] == "user"
    assert formatted["input"]["messages"][0]["content"] == "Hello"
    assert formatted["input"]["messages"][1]["role"] == "assistant"
    assert formatted["input"]["messages"][1]["content"] == "Hi there!"
    
    # Verify no system message was added
    assert all(msg["role"] != "system" for msg in formatted["input"]["messages"])


def test_dashscope_chat_formatter_with_system():
    """Test DashScopeChatFormatter when system message is provided."""
    # Initialize formatter with API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    formatter = DashScopeChatFormatter(api_key=api_key)
    
    # Create test messages with system message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    # Format the messages
    formatted = formatter.format(messages)
    
    # Assertions from original test
    assert isinstance(formatted, dict)
    assert "input" in formatted
    assert "parameters" in formatted
    
    # Check that messages are properly formatted
    assert len(formatted["input"]["messages"]) == 3
    assert formatted["input"]["messages"][0]["role"] == "system"
    assert formatted["input"]["messages"][0]["content"] == "You are a helpful assistant."
    assert formatted["input"]["messages"][1]["role"] == "user"
    assert formatted["input"]["messages"][1]["content"] == "Hello"


def test_dashscope_chat_formatter_empty_messages():
    """Test DashScopeChatFormatter with empty messages list."""
    # Initialize formatter with API key from environment
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    formatter = DashScopeChatFormatter(api_key=api_key)
    
    # Test with empty messages
    messages = []
    
    # Format the messages
    formatted = formatter.format(messages)
    
    # Assertions
    assert isinstance(formatted, dict)
    assert "input" in formatted
    assert "parameters" in formatted
    assert formatted["input"]["messages"] == []


def test_dashscope_chat_formatter_model_override():
    """Test DashScopeChatFormatter with model override."""
    # Initialize formatter with custom model
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    formatter = DashScopeChatFormatter(api_key=api_key, model="qwen-max")
    
    # Create test messages
    messages = [
        {"role": "user", "content": "Test message"}
    ]
    
    # Format the messages
    formatted = formatter.format(messages)
    
    # Assertions
    assert isinstance(formatted, dict)
    assert "model" in formatted
    assert formatted["model"] == "qwen-max"


@patch('litellm.completion')
def test_dashscope_chat_formatter_integration(mock_litellm):
    """Integration test for DashScopeChatFormatter with mocked API call."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {"content": "Mocked response"}
    mock_litellm.return_value = mock_response
    
    # Initialize formatter
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    formatter = DashScopeChatFormatter(api_key=api_key)
    
    # Create test messages
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    # Format and make call
    formatted = formatter.format(messages)
    
    # Verify litellm was called with correct parameters
    mock_litellm.assert_called_once()
    call_args = mock_litellm.call_args[1]
    
    assert call_args["model"] == "dashscope/qwen-plus"
    assert call_args["messages"] == formatted["input"]["messages"]
    assert call_args["api_key"] == api_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])