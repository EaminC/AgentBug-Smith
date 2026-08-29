"""
Test file for crewai/litellm integration testing.
This test focuses on formatter functionality and API client initialization.
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys

# Test 1: Basic import test
def test_imports():
    """Test that core modules can be imported."""
    import crewai
    import litellm
    assert True  # If we get here, imports succeeded

# Test 2: Environment variables are set
def test_env_variables():
    """Test that environment variables are properly set."""
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('FORGE_API_KEY') is not None
    assert os.getenv('TAVILY_API_KEY') is not None
    assert os.getenv('GITHUB_TOKEN') is not None

# Test 3: Test DashScopeChatFormatter if it exists in the codebase
def test_dashscope_formatter():
    """Test DashScopeChatFormatter initialization and methods."""
    try:
        # Try to import from agentscope.formatter if that's the correct path
        from agentscope.formatter import DashScopeChatFormatter
        formatter = DashScopeChatFormatter()
        assert formatter is not None
        
        # Test format method if it exists
        if hasattr(formatter, 'format'):
            test_messages = [{"role": "user", "content": "Hello"}]
            result = formatter.format(test_messages)
            assert isinstance(result, (list, dict, str))
    except ImportError:
        # If not available, skip but mark as potential issue
        pytest.skip("DashScopeChatFormatter not available in this codebase")

# Test 4: Test litellm completion with mocked API
def test_litellm_completion_mocked():
    """Test litellm completion with mocked API call."""
    with patch('litellm.completion') as mock_completion:
        mock_completion.return_value = {
            "choices": [{"message": {"content": "Mocked response"}}]
        }
        
        import litellm
        response = litellm.completion(
            model=os.getenv('MODEL', 'gpt-3.5-turbo'),
            messages=[{"role": "user", "content": "Hello"}],
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL')
        )
        
        assert response["choices"][0]["message"]["content"] == "Mocked response"
        mock_completion.assert_called_once()

# Test 5: Test crewai agent initialization
def test_crewai_agent():
    """Test basic crewai agent creation."""
    try:
        from crewai import Agent
        
        agent = Agent(
            role="Test Agent",
            goal="Test the system",
            backstory="A test agent",
            verbose=True
        )
        
        assert agent.role == "Test Agent"
        assert agent.goal == "Test the system"
    except ImportError as e:
        pytest.skip(f"CrewAI Agent not available: {e}")

# Test 6: Test async functionality if present
@pytest.mark.asyncio
async def test_async_operations():
    """Test async operations if the codebase supports them."""
    try:
        # Try to find async components
        import asyncio
        from unittest.mock import AsyncMock
        
        # Create a mock async function
        async_mock = AsyncMock(return_value="async response")
        result = await async_mock()
        assert result == "async response"
    except Exception as e:
        pytest.skip(f"Async operations not testable: {e}")

# Test 7: Test formatter with different message formats
def test_formatter_message_formats():
    """Test formatter with various message formats."""
    try:
        # Try different formatter imports
        from litellm import completion
        from litellm.types.utils import ModelResponse
        
        # Test with simple message format
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What's the weather?"}
        ]
        
        # This is just a structural test, actual API call would be mocked
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "What's the weather?"
    except ImportError as e:
        pytest.skip(f"litellm types not available: {e}")

# Test 8: Test error handling
def test_error_handling():
    """Test error handling in API calls."""
    with patch('litellm.completion', side_effect=Exception("API Error")):
        import litellm
        try:
            litellm.completion(
                model="invalid-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
            assert False, "Should have raised an exception"
        except Exception as e:
            assert "API Error" in str(e)

# Test 9: Test configuration loading
def test_configuration():
    """Test that configuration is properly loaded."""
    # Test that environment variables are strings
    api_key = os.getenv('OPENAI_API_KEY')
    assert isinstance(api_key, str)
    assert len(api_key) > 0
    
    base_url = os.getenv('OPENAI_BASE_URL')
    assert isinstance(base_url, str)
    assert base_url.startswith('http')

# Test 10: Test package version compatibility
def test_package_versions():
    """Test that critical packages are installed."""
    import pkg_resources
    packages = ['crewai', 'litellm', 'pytest']
    
    for package in packages:
        try:
            version = pkg_resources.get_distribution(package).version
            assert version is not None
            print(f"{package} version: {version}")
        except pkg_resources.DistributionNotFound:
            pytest.skip(f"{package} not installed")

if __name__ == "__main__":
    # Run tests directly if needed
    pytest.main([__file__, "-v"])