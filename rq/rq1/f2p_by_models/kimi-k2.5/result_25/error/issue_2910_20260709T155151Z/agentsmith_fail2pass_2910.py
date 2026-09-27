# test_f2p.py - Fail-to-Pass environment validation test
import os
import sys
import pytest

# Ensure src layout is accessible
sys.path.insert(0, '/app/src')

# Import from the actual crewai package
from crewai import __version__, Agent, Task, Crew

def test_crewai_package_import():
    """Verify crewai package is properly installed and importable."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0

def test_crewai_agent_instantiation():
    """Verify Agent class can be instantiated with minimal config."""
    # This validates the environment setup without requiring API calls
    agent = Agent(
        role="Test Role",
        goal="Test Goal",
        backstory="Test Backstory",
        allow_delegation=False,
        verbose=False
    )
    assert agent is not None
    assert agent.role == "Test Role"
    assert agent.goal == "Test Goal"

def test_environment_variables_loaded():
    """Verify critical environment variables are present."""
    assert os.getenv("OPENAI_API_KEY") is not None
    assert os.getenv("OPENAI_BASE_URL") is not None
    assert os.getenv("PYTHONPATH") == "/app/src"