"""
Test file for DashScopeChatFormatter bug reproduction.
Based on the instructions mentioning tests/formatter_dashscope_test.py
and the need to test the real imported code.
"""

import pytest
import os
from unittest.mock import patch, MagicMock


def test_dashscope_chat_formatter_basic():
    """
    Basic test for DashScopeChatFormatter to ensure it can be imported
    and instantiated without errors.
    """
    try:
        # Try to import the actual module from agentscope
        from agentscope.formatter import DashScopeChatFormatter
        
        # Create an instance with minimal configuration
        # Using environment variable for API key as per instructions
        api_key = os.getenv('OPENAI_API_KEY', 'test-key')
        
        # Mock the underlying API client to avoid actual network calls
        with patch('litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            
            formatter = DashScopeChatFormatter(
                model="qwen-turbo",
                api_key=api_key
            )
            
            # Test basic formatting
            messages = [{"role": "user", "content": "Hello"}]
            formatted = formatter.format(messages)
            
            # Basic assertion - the formatter should return something
            assert formatted is not None
            
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")
    except Exception as e:
        # If there's a bug in the formatter, this test should fail
        pytest.fail(f"Error instantiating or using DashScopeChatFormatter: {e}")


def test_dashscope_chat_formatter_with_system_message():
    """
    Test that system messages are properly handled by the formatter.
    This is a common area for bugs in chat formatters.
    """
    try:
        from agentscope.formatter import DashScopeChatFormatter
        
        api_key = os.getenv('OPENAI_API_KEY', 'test-key')
        
        with patch('litellm.completion') as mock_completion:
            mock_completion.return_value = {
                'choices': [{'message': {'content': 'Test response'}}]
            }
            
            formatter = DashScopeChatFormatter(
                model="qwen-turbo",
                api_key=api_key
            )
            
            # Test with system message
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"}
            ]
            
            formatted = formatter.format(messages)
            assert formatted is not None
            
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")


def test_dashscope_chat_formatter_error_handling():
    """
    Test error handling in the formatter.
    """
    try:
        from agentscope.formatter import DashScopeChatFormatter
        
        api_key = os.getenv('OPENAI_API_KEY', 'test-key')
        
        formatter = DashScopeChatFormatter(
            model="qwen-turbo",
            api_key=api_key
        )
        
        # Test with invalid messages
        with pytest.raises(Exception):
            formatter.format([])
            
    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])