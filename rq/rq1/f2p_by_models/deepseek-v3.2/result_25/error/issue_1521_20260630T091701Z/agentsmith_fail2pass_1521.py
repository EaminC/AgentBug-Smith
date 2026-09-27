import os
import pytest
from unittest.mock import Mock, patch, AsyncMock


def test_environment_variables_are_set():
    """Test that required environment variables are properly set."""
    # Test that critical environment variables are present
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('OPENAI_BASE_URL') is not None
    assert os.getenv('FORGE_API_KEY') is not None
    assert os.getenv('TAVILY_API_KEY') is not None
    assert os.getenv('GITHUB_TOKEN') is not None
    
    # Test specific values match expected patterns
    assert 'forge-' in os.getenv('OPENAI_API_KEY', '')
    assert 'api.forge.tensorblock.co' in os.getenv('OPENAI_BASE_URL', '')


@pytest.mark.asyncio
async def test_openai_client_initialization():
    """Test OpenAI client initialization with environment variables."""
    from openai import OpenAI
    
    # Mock the actual API call to avoid network requests
    with patch('openai.OpenAI') as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Initialize client
        client = OpenAI(
            base_url=os.getenv('OPENAI_BASE_URL'),
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Verify client was initialized with correct parameters
        mock_openai_class.assert_called_once_with(
            base_url=os.getenv('OPENAI_BASE_URL'),
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Test a mock API call
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        response = client.chat.completions.create(
            model=os.getenv('MODEL'),
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        assert response.choices[0].message.content == "Test response"


def test_crewai_import():
    """Test that crewai can be imported successfully."""
    import crewai
    # Basic assertion to ensure module has expected attributes
    assert hasattr(crewai, '__version__') or hasattr(crewai, 'Agent') or hasattr(crewai, 'Crew')


def test_langchain_import():
    """Test that langchain can be imported successfully."""
    import langchain
    # Basic assertion to ensure module exists
    assert langchain is not None


@pytest.mark.asyncio
async def test_async_operations():
    """Test asynchronous operations with proper async/await patterns."""
    # Create a simple async function to test async capabilities
    async def async_test_function():
        return "async_test_passed"
    
    result = await async_test_function()
    assert result == "async_test_passed"


def test_pydantic_models():
    """Test Pydantic model functionality."""
    from pydantic import BaseModel
    
    class TestModel(BaseModel):
        name: str
        value: int
    
    # Test model instantiation
    instance = TestModel(name="test", value=42)
    assert instance.name == "test"
    assert instance.value == 42
    
    # Test model validation
    with pytest.raises(ValueError):
        TestModel(name=123, value="not_an_int")


if __name__ == "__main__":
    # Run tests directly if needed
    pytest.main([__file__, "-v"])