"""
Test file for agentscope/litellm functionality.
This is a minimal test based on the environment setup.
"""
import os
import pytest
import asyncio

def test_environment_variables():
    """Test that environment variables are set correctly."""
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('OPENAI_BASE_URL') is not None
    assert os.getenv('MODEL') is not None
    print("Environment variables are set")

def test_litellm_import():
    """Test that litellm can be imported."""
    try:
        import litellm
        assert litellm is not None
        print("litellm imported successfully")
    except ImportError as e:
        pytest.fail(f"Failed to import litellm: {e}")

def test_agentscope_import():
    """Test that agentscope can be imported if available."""
    try:
        # Try to import agentscope if it exists
        import agentscope
        assert agentscope is not None
        print("agentscope imported successfully")
    except ImportError:
        # This is okay if agentscope is not in the project
        print("agentscope not found in project")

@pytest.mark.asyncio
async def test_async_operations():
    """Test basic async functionality."""
    await asyncio.sleep(0.1)
    assert True

if __name__ == "__main__":
    # Run basic tests
    test_environment_variables()
    test_litellm_import()
    test_agentscope_import()
    print("All basic tests passed")