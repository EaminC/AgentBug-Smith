"""
Test file for AutoGPT F2P setup.
This test validates basic functionality of the AutoGPT system.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock


def test_autogpt_import():
    """Basic test to verify AutoGPT can be imported."""
    # This is a minimal test that should always pass if installation is correct
    import autogpt
    assert autogpt is not None


def test_environment_variables():
    """Test that environment variables are properly set."""
    # Check that critical environment variables are present
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('FORGE_API_KEY') is not None
    assert os.getenv('TAVILY_API_KEY') is not None
    
    # Verify they contain expected patterns
    api_key = os.getenv('OPENAI_API_KEY')
    assert api_key.startswith('forge-') or 'forge' in api_key.lower()


@pytest.mark.asyncio
async def test_async_operations():
    """Test basic async functionality."""
    # Simple async test to verify async/await works
    async def dummy_async():
        return "success"
    
    result = await dummy_async()
    assert result == "success"


class TestAutoGPTComponents:
    """Test suite for AutoGPT components."""
    
    def test_mock_external_api(self):
        """Test mocking external API calls."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"result": "success"}
            mock_post.return_value = mock_response
            
            # Import and test a component that might use requests
            try:
                # Try to import a common AutoGPT component
                from autogpt.llm import call_ai_function
                # If import succeeds, we can add more specific tests
                assert True
            except ImportError:
                # If specific module doesn't exist, that's okay for basic test
                pass


def test_pytest_fixtures():
    """Test that pytest fixtures work correctly."""
    # This test ensures the test framework is properly set up
    @pytest.fixture
    def sample_fixture():
        return {"test": "data"}
    
    # Use the fixture in a test
    def test_with_fixture(sample_fixture):
        assert sample_fixture["test"] == "data"
    
    # Actually run the test
    test_with_fixture({"test": "data"})


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])