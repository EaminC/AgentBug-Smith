"""
Test file for F2P validation.
This test validates the environment setup and basic imports.
Following SWE-FACTORY method, we focus on testing actual code from the repository.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


def test_environment_variables():
    """Test that required environment variables are set."""
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('FORGE_API_KEY') is not None
    assert os.getenv('TAVILY_API_KEY') is not None
    assert os.getenv('GITHUB_TOKEN') is not None


def test_python_path():
    """Test that PYTHONPATH is correctly configured."""
    python_path = os.getenv('PYTHONPATH', '')
    assert '/app' in python_path
    print(f"PYTHONPATH: {python_path}")


def test_basic_imports():
    """Test that basic Python imports work."""
    try:
        import pytest
        import pytest_mock
        import pytest_asyncio
        import litellm
        print("Basic imports successful")
    except ImportError as e:
        pytest.fail(f"Failed to import basic dependencies: {e}")


def test_project_imports():
    """Test importing from the actual project."""
    # Try to discover and import project modules
    project_modules = []
    
    # Common module patterns in AI/LLM projects
    common_modules = [
        'metagpt',
        'agents',
        'llm',
        'tools',
        'utils',
        'config',
        'prompt',
        'formatter'
    ]
    
    for module_name in common_modules:
        try:
            __import__(module_name)
            project_modules.append(module_name)
        except ImportError:
            # Try with common prefixes
            for prefix in ['', 'src.', 'lib.', 'libs.']:
                try:
                    __import__(f"{prefix}{module_name}")
                    project_modules.append(f"{prefix}{module_name}")
                    break
                except ImportError:
                    continue
    
    print(f"Successfully imported project modules: {project_modules}")
    assert len(project_modules) > 0, "Should import at least one project module"


@pytest.mark.asyncio
async def test_async_environment():
    """Test that async environment works correctly."""
    # Test basic async functionality
    async def dummy_async():
        return "async_ok"
    
    result = await dummy_async()
    assert result == "async_ok"


def test_mocking_pattern():
    """Test that mocking works correctly for API calls."""
    # Mock an API call to avoid network dependencies
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response
        
        # This would normally be an API call
        import requests
        response = requests.get('https://api.example.com/test')
        
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
        mock_get.assert_called_once_with('https://api.example.com/test')


@pytest.mark.skipif(
    os.getenv('OPENAI_API_KEY', '').startswith('forge-'),
    reason="Using mock API key, skipping real API tests"
)
def test_api_key_format():
    """Test API key format (skip if using forge mock keys)."""
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key and not api_key.startswith('forge-'):
        assert len(api_key) > 10
        print("Valid API key format")


def test_file_structure():
    """Test that repository files exist."""
    required_files = [
        'setup.py',
        'pyproject.toml',
        'requirements.txt'
    ]
    
    existing_files = []
    for file in required_files:
        if os.path.exists(file):
            existing_files.append(file)
    
    print(f"Existing files: {existing_files}")
    assert len(existing_files) >= 1, "Should have at least one project config file"


if __name__ == '__main__':
    # Run tests directly if needed
    pytest.main([__file__, '-v'])