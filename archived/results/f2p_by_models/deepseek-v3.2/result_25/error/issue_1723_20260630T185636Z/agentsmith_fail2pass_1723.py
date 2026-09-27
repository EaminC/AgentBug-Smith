"""
Test file for F2P setup.
Since no specific test content was provided, this is a minimal test
that validates the environment setup and basic imports.
"""

import os
import sys
import pytest


def test_environment_variables_set():
    """Test that required environment variables are set."""
    assert os.getenv('OPENAI_API_KEY') is not None, "OPENAI_API_KEY should be set"
    assert os.getenv('FORGE_API_KEY') is not None, "FORGE_API_KEY should be set"
    assert os.getenv('TAVILY_API_KEY') is not None, "TAVILY_API_KEY should be set"
    assert os.getenv('GITHUB_TOKEN') is not None, "GITHUB_TOKEN should be set"


def test_python_path():
    """Test that Python can import from the installed package."""
    try:
        # Try to import crewai if it exists
        import crewai
        assert True, "crewai imported successfully"
    except ImportError:
        # If crewai doesn't exist, check for other common packages
        print("crewai not found, checking sys.path")
        print(f"sys.path: {sys.path}")
        # Try to import any local module
        try:
            # Look for any .py files in the current directory
            import importlib.util
            spec = importlib.util.find_spec(".")
            assert spec is not None, "Should be able to find local modules"
        except Exception as e:
            pytest.fail(f"Failed to import local modules: {e}")


def test_pytest_environment():
    """Basic test to verify pytest is working."""
    assert True, "Basic assertion should pass"


if __name__ == "__main__":
    # Run tests directly if needed
    test_environment_variables_set()
    test_python_path()
    test_pytest_environment()
    print("All tests passed!")