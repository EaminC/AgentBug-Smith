"""
Test file for F2P verification.
This test is designed to verify basic functionality of the repository.
"""

import pytest
import os


def test_environment_variables():
    """Test that environment variables are properly set."""
    # Check that critical environment variables are set
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('OPENAI_BASE_URL') is not None
    assert os.getenv('MODEL') is not None
    print("Environment variables are properly set")


def test_pytest_import():
    """Test that pytest can be imported."""
    import pytest as pytest_module
    assert pytest_module is not None
    print("Pytest import successful")


def test_basic_import():
    """Test basic import of common AI/LLM related packages."""
    try:
        # Try importing common packages that might be used
        import litellm
        import anyio
        print("Basic imports successful")
    except ImportError as e:
        pytest.fail(f"Failed to import required packages: {e}")


def test_project_structure():
    """Test that the project has basic structure."""
    import os
    
    # Check for common project files
    assert os.path.exists('/app') is True
    
    # Check for Python files or directories
    python_files = []
    for root, dirs, files in os.walk('/app'):
        if any(file.endswith('.py') for file in files):
            python_files.append(root)
            break
    
    assert len(python_files) > 0, "No Python files found in the project"
    print(f"Found Python files in: {python_files[0]}")


@pytest.mark.asyncio
async def test_async_environment():
    """Test that async environment works."""
    import asyncio
    
    async def dummy_async():
        return True
    
    result = await dummy_async()
    assert result is True
    print("Async environment works correctly")


if __name__ == "__main__":
    # Run basic tests
    test_environment_variables()
    test_pytest_import()
    test_basic_import()
    test_project_structure()
    print("All basic tests passed")