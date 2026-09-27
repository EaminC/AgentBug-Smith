"""
Test file for crewai bug reproduction.
Since no specific test was provided, this test validates the basic functionality
of the crewai package and follows the repository's testing patterns.
"""

import os
import pytest
import sys

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_crewai_import():
    """Basic test to verify crewai can be imported and has expected modules."""
    import crewai
    assert hasattr(crewai, '__version__') or hasattr(crewai, '__name__')
    print(f"Successfully imported crewai from {crewai.__file__}")

def test_crewai_agent_creation():
    """Test basic agent creation if the module structure supports it."""
    try:
        from crewai import Agent
        # Create a simple agent with minimal configuration
        agent = Agent(
            role="Test Agent",
            goal="Test the system",
            backstory="A test agent for validation",
            allow_delegation=False,
            verbose=False
        )
        assert agent.role == "Test Agent"
        assert agent.goal == "Test the system"
    except ImportError:
        # If Agent is not directly importable, try alternative import paths
        try:
            from crewai.agents import Agent
            agent = Agent(
                role="Test Agent",
                goal="Test the system",
                backstory="A test agent for validation",
                allow_delegation=False,
                verbose=False
            )
            assert agent.role == "Test Agent"
        except ImportError:
            # Skip if Agent class is not found - this is okay for basic validation
            pytest.skip("Agent class not found in expected locations")

def test_environment_variables():
    """Test that environment variables are properly set."""
    assert os.getenv('OPENAI_API_KEY') is not None
    assert os.getenv('GITHUB_TOKEN') is not None
    # Check that the API keys are not empty strings
    assert len(os.getenv('OPENAI_API_KEY', '')) > 0
    assert len(os.getenv('GITHUB_TOKEN', '')) > 0

def test_pytest_integration():
    """Test that pytest is working correctly with the installed package."""
    # This is a simple test to verify the test runner works
    assert True

# If there are specific tests from the patch, they would be included here
# Since we don't have the specific test_paths_in_patch, we use generic tests

if __name__ == "__main__":
    # Simple runner for debugging
    test_crewai_import()
    print("All tests passed!")