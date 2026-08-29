"""
Test file for agentscope formatter functionality.
This test replicates the structure from the repository's test suite.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Try to import from agentscope based on common patterns
try:
    from agentscope.formatter import DashScopeChatFormatter
    HAS_DASHSCOPE = True
except ImportError:
    HAS_DASHSCOPE = False

try:
    from agentscope.formatter import OpenAIChatFormatter
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from agentscope.formatter import FormatterBase
    HAS_BASE = True
except ImportError:
    HAS_BASE = False


class TestFormatterBase:
    """Test base formatter functionality."""
    
    def test_formatter_base_initialization(self):
        """Test FormatterBase initialization."""
        if not HAS_BASE:
            pytest.skip("FormatterBase not available")
        
        # Test basic initialization
        formatter = FormatterBase()
        assert formatter is not None
        
        # Test with custom parameters
        formatter = FormatterBase(system_prompt="You are a helpful assistant")
        assert formatter.system_prompt == "You are a helpful assistant"


class TestDashScopeChatFormatter:
    """Test DashScopeChatFormatter functionality."""
    
    def test_dashscope_formatter_initialization(self):
        """Test DashScopeChatFormatter initialization."""
        if not HAS_DASHSCOPE:
            pytest.skip("DashScopeChatFormatter not available")
        
        # Test basic initialization
        formatter = DashScopeChatFormatter()
        assert formatter is not None
        
        # Test with custom system prompt
        formatter = DashScopeChatFormatter(
            system_prompt="You are a helpful assistant"
        )
        assert formatter.system_prompt == "You are a helpful assistant"
    
    def test_dashscope_format_messages(self):
        """Test message formatting for DashScope."""
        if not HAS_DASHSCOPE:
            pytest.skip("DashScopeChatFormatter not available")
        
        formatter = DashScopeChatFormatter()
        
        # Test with simple messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        formatted = formatter.format_messages(messages)
        assert formatted is not None
        assert isinstance(formatted, list)
        
        # Test with system message
        messages_with_system = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]
        
        formatted = formatter.format_messages(messages_with_system)
        assert formatted is not None
    
    @patch('agentscope.formatter.dashscope.AzureOpenAI')
    def test_dashscope_with_mocked_client(self, mock_azure_openai):
        """Test DashScope formatter with mocked client."""
        if not HAS_DASHSCOPE:
            pytest.skip("DashScopeChatFormatter not available")
        
        # Setup mock
        mock_client = MagicMock()
        mock_azure_openai.return_value = mock_client
        
        # Mock the chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Mocked response"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Test formatter with mocked client
        formatter = DashScopeChatFormatter()
        
        # This would normally call the API, but is mocked
        messages = [{"role": "user", "content": "Test"}]
        
        # Note: The actual API call would be in a different method
        # This test verifies the formatter can be instantiated with mocked dependencies


class TestOpenAIChatFormatter:
    """Test OpenAIChatFormatter functionality."""
    
    def test_openai_formatter_initialization(self):
        """Test OpenAIChatFormatter initialization."""
        if not HAS_OPENAI:
            pytest.skip("OpenAIChatFormatter not available")
        
        # Test basic initialization
        formatter = OpenAIChatFormatter()
        assert formatter is not None
        
        # Test with custom parameters
        formatter = OpenAIChatFormatter(
            model="gpt-4",
            temperature=0.5
        )
        # Check that parameters are set
        assert hasattr(formatter, 'model')
    
    def test_openai_format_messages(self):
        """Test message formatting for OpenAI."""
        if not HAS_OPENAI:
            pytest.skip("OpenAIChatFormatter not available")
        
        formatter = OpenAIChatFormatter()
        
        # Test with simple messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        formatted = formatter.format_messages(messages)
        assert formatted is not None
        assert isinstance(formatted, list)
        
        # Verify structure
        if formatted and len(formatted) > 0:
            assert 'role' in formatted[0]
            assert 'content' in formatted[0]


def test_environment_variables():
    """Test that environment variables are accessible."""
    # Test that we can read environment variables
    api_key = os.getenv('OPENAI_API_KEY')
    assert api_key is not None
    
    # Test other environment variables
    base_url = os.getenv('OPENAI_BASE_URL')
    assert base_url is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])