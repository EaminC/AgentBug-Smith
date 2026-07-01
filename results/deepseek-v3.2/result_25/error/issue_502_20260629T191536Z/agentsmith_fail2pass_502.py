import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json

# Test for DashScopeChatFormatter bug fix
# Based on the issue: DashScopeChatFormatter incorrectly handles system messages
# The fix ensures system messages are properly formatted in the messages list

def test_dashscope_chat_formatter_system_message():
    """Test that DashScopeChatFormatter correctly handles system messages."""
    
    # Import the actual formatter from the repository
    # Assuming the package structure based on common patterns
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        # Try alternative import path
        from src.agentscope.formatter import DashScopeChatFormatter
    
    # Create formatter instance
    formatter = DashScopeChatFormatter()
    
    # Test case 1: Single system message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]
    
    formatted = formatter.format(messages)
    
    # Check that system message is preserved
    assert len(formatted) == 1
    assert formatted[0]["role"] == "system"
    assert formatted[0]["content"] == "You are a helpful assistant."
    
    # Test case 2: Mixed messages with system message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    formatted = formatter.format(messages)
    
    # Check all messages are preserved in order
    assert len(formatted) == 3
    assert formatted[0]["role"] == "system"
    assert formatted[0]["content"] == "You are a helpful assistant."
    assert formatted[1]["role"] == "user"
    assert formatted[1]["content"] == "Hello!"
    assert formatted[2]["role"] == "assistant"
    assert formatted[2]["content"] == "Hi there!"
    
    # Test case 3: No system message
    messages = [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    formatted = formatter.format(messages)
    
    assert len(formatted) == 2
    assert formatted[0]["role"] == "user"
    assert formatted[0]["content"] == "Hello!"
    assert formatted[1]["role"] == "assistant"
    assert formatted[1]["content"] == "Hi there!"
    
    # Test case 4: Multiple system messages (edge case)
    messages = [
        {"role": "system", "content": "First system message."},
        {"role": "system", "content": "Second system message."},
        {"role": "user", "content": "Hello!"}
    ]
    
    formatted = formatter.format(messages)
    
    # Both system messages should be preserved
    assert len(formatted) == 3
    assert formatted[0]["role"] == "system"
    assert formatted[0]["content"] == "First system message."
    assert formatted[1]["role"] == "system"
    assert formatted[1]["content"] == "Second system message."
    assert formatted[2]["role"] == "user"
    assert formatted[2]["content"] == "Hello!"

def test_dashscope_chat_formatter_with_model():
    """Test DashScopeChatFormatter with model parameter."""
    
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        from src.agentscope.formatter import DashScopeChatFormatter
    
    # Test with model parameter
    formatter = DashScopeChatFormatter(model="qwen-plus")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    
    formatted = formatter.format(messages)
    
    assert len(formatted) == 2
    assert formatted[0]["role"] == "system"
    assert formatted[0]["content"] == "You are a helpful assistant."
    assert formatted[1]["role"] == "user"
    assert formatted[1]["content"] == "Hello!"

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_async():
    """Test async usage of DashScopeChatFormatter."""
    
    try:
        from agentscope.formatter import DashScopeChatFormatter
    except ImportError:
        from src.agentscope.formatter import DashScopeChatFormatter
    
    formatter = DashScopeChatFormatter()
    
    # Mock the underlying API call if needed
    with patch('litellm.acompletion', new_callable=AsyncMock) as mock_acompletion:
        mock_acompletion.return_value = {
            "choices": [{"message": {"content": "Mocked response"}}]
        }
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
        
        # Test that formatter can be used in async context
        formatted = formatter.format(messages)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"

if __name__ == "__main__":
    # Run tests directly
    test_dashscope_chat_formatter_system_message()
    test_dashscope_chat_formatter_with_model()
    print("All tests passed!")