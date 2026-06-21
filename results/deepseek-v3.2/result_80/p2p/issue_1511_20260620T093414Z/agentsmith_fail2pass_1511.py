import pytest
import os

def test_environment_variables():
    """Test that environment variables are set correctly."""
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('OPENAI_BASE_URL') is not None
    assert os.getenv('ANTHROPIC_AUTH_TOKEN') is not None
    assert os.getenv('ANTHROPIC_BASE_URL') is not None

def test_basic_imports():
    """Test that basic Python imports work."""
    # Test standard library imports
    import sys
    import json
    import asyncio
    
    # Test third-party imports that were installed
    import pytest
    import litellm
    
    # Try to import from the local project
    # This is a generic test - in practice, you would import actual modules
    # from your repository
    try:
        # Try to find and import a module from the project
        # This is a safe way to test if the editable install worked
        import importlib.util
        import pathlib
        
        # Look for Python files in the current directory
        project_root = pathlib.Path('.')
        python_files = list(project_root.rglob('*.py'))
        
        if python_files:
            print(f"Found Python files: {[f.name for f in python_files[:5]]}")
            
    except Exception as e:
        print(f"Import test note: {e}")
        # Don't fail the test - this is just informational

@pytest.mark.asyncio
async def test_async_support():
    """Test that async/await works correctly."""
    async def dummy_async():
        return True
    
    result = await dummy_async()
    assert result is True

if __name__ == "__main__":
    # Run basic tests
    test_environment_variables()
    test_basic_imports()
    
    # Run async test
    import asyncio
    asyncio.run(test_async_support())
    
    print("All basic tests passed!")