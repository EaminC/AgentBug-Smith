import pytest
import os

def test_environment_variables_set():
    """Test that environment variables are properly set for API connections"""
    # Check that critical environment variables are set
    assert os.getenv('OPENAI_API_KEY') is not None, "OPENAI_API_KEY should be set"
    assert os.getenv('OPENAI_BASE_URL') is not None, "OPENAI_BASE_URL should be set"
    assert os.getenv('TAVILY_API_KEY') is not None, "TAVILY_API_KEY should be set"
    
    # Test that the keys are not empty strings
    assert len(os.getenv('OPENAI_API_KEY', '')) > 0, "OPENAI_API_KEY should not be empty"
    assert len(os.getenv('OPENAI_BASE_URL', '')) > 0, "OPENAI_BASE_URL should not be empty"

def test_autogpt_import():
    """Test that autogpt package can be imported"""
    try:
        # Try to import autogpt or related modules
        import autogpt
        assert True, "autogpt imported successfully"
    except ImportError as e:
        pytest.fail(f"Failed to import autogpt: {e}")

def test_pytest_plugins_available():
    """Test that pytest plugins are properly installed"""
    import pytest_mock
    import pytest_asyncio
    import pytest_cov
    assert True, "All pytest plugins are available"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])