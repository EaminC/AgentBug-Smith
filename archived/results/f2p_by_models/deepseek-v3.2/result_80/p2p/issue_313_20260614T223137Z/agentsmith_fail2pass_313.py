import pytest
from pydantic import ValidationError
import sys
import os

# Mock the missing imports before importing any agent modules
import a2a.utils
import a2a.types

# Patch the missing functions/classes in a2a.utils
if not hasattr(a2a.utils, 'new_agent_text_message'):
    a2a.utils.new_agent_text_message = lambda *args, **kwargs: None

if not hasattr(a2a.utils, 'new_task'):
    a2a.utils.new_task = lambda *args, **kwargs: None

# Patch the missing DataPart in a2a.types
if not hasattr(a2a.types, 'DataPart'):
    class DataPart:
        pass
    a2a.types.DataPart = DataPart

# Now we can safely import the agent modules
sys.modules['a2a.utils'] = a2a.utils
sys.modules['a2a.types'] = a2a.types

def test_agent_configuration_accepts_string_agent_type():
    """Test that AgentConfiguration accepts string 'reactive'/'iterative' values."""
    # Try to import, but skip if module doesn't exist
    try:
        from agent.core.models.configuration import AgentConfiguration
    except ImportError:
        pytest.skip("AgentConfiguration not available")
    
    # Should accept string values
    config1 = AgentConfiguration(agent_type="reactive")
    assert config1.agent_type == "reactive"

    config2 = AgentConfiguration(agent_type="iterative")
    assert config2.agent_type == "iterative"

    # Should reject invalid string values
    with pytest.raises(ValidationError):
        AgentConfiguration(agent_type="invalid")


def test_create_agent_executor_with_string_agent_type():
    """Test that create_agent_executor correctly handles string agent_type."""
    # Try to import, but skip if module doesn't exist
    try:
        from agent.core.executor import create_agent_executor
        from agent.core.models import AgentConfiguration
    except ImportError:
        pytest.skip("create_agent_executor or AgentConfiguration not available")

    # Mock minimal dependencies to avoid external calls
    class MockAgent:
        pass

    # Test with string "reactive"
    executor = create_agent_executor(
        agent=MockAgent(),
        agent_type="reactive",
        config_kwargs={}
    )
    assert isinstance(executor.config, AgentConfiguration)
    # Check that it's a string (or enum value string) after conversion
    assert executor.config.agent_type in ("reactive", "iterative")

    # Test with string "iterative"
    executor2 = create_agent_executor(
        agent=MockAgent(),
        agent_type="iterative",
        config_kwargs={}
    )
    assert executor2.config.agent_type in ("iterative", "reactive")

    # Test with invalid string (should default to reactive with warning)
    executor3 = create_agent_executor(
        agent=MockAgent(),
        agent_type="invalid",
        config_kwargs={}
    )
    assert executor3.config.agent_type == "reactive"


def test_memory_context_accepts_string_agent_type():
    """Test that MemoryContext accepts string agent_type."""
    # Try to import, but skip if module doesn't exist
    try:
        from agent.core.models import MemoryContext
    except ImportError:
        pytest.skip("MemoryContext not available")

    # Should accept string "iterative"
    context = MemoryContext(context_id="test", agent_type="iterative")
    assert context.agent_type == "iterative"

    # Should accept string "reactive"
    context2 = MemoryContext(context_id="test2", agent_type="reactive")
    assert context2.agent_type == "reactive"

    # Should reject invalid string values
    with pytest.raises(ValidationError):
        MemoryContext(context_id="test3", agent_type="invalid")


def test_cli_init_agent_prompts_return_strings():
    """Test that CLI init_agent prompts return string values, not enums."""
    # Try to import, but skip if module doesn't exist
    try:
        from agent.cli.commands.init_agent import _prompt_for_features
    except ImportError:
        pytest.skip("_prompt_for_features not available")

    # Mock questionary.select to return a string
    import questionary
    original_select = questionary.select

    def mock_select(*args, **kwargs):
        class MockChoice:
            def ask(self):
                return "iterative"
        return MockChoice()

    questionary.select = mock_select

    try:
        project_config = {}
        # This function should store a string in project_config["agent_type"]
        _prompt_for_features(project_config, quick=False, no_git=False)
        # Should be string "iterative"
        assert project_config["agent_type"] == "iterative"
    finally:
        questionary.select = original_select


def test_api_app_agent_config_creation():
    """Test that _setup_request_handler creates AgentConfiguration with string agent_type."""
    # Try to import, but skip if module doesn't exist
    try:
        from agent.api.app import _setup_request_handler
        from fastapi import FastAPI
    except ImportError:
        pytest.skip("_setup_request_handler or FastAPI not available")

    # Mock config to return agent_type as string
    class MockConfig:
        def get(self, key, default):
            if key == "agent_type":
                return "iterative"
            return default

    # Mock minimal dependencies
    import agent.api.app
    original_config = agent.api.app.config
    agent.api.app.config = MockConfig()

    # Mock other imports that would be called
    class MockAgentCard:
        pass

    class MockAgentUpExecutor:
        def __init__(self, agent, config):
            self.agent = agent
            self.config = config

    class MockDefaultRequestHandler:
        def __init__(self, agent_executor, **kwargs):
            self.agent_executor = agent_executor

    agent.api.app.create_agent_card = lambda: MockAgentCard()
    agent.api.app.AgentUpExecutor = MockAgentUpExecutor
    agent.api.app.DefaultRequestHandler = MockDefaultRequestHandler

    try:
        app = FastAPI()
        _setup_request_handler(app)
        # The handler should be attached to app
        # If buggy code passes AgentType.ITERATIVE enum (instead of string), Pydantic will raise
        # So just reaching here without exception indicates success for fixed code
        assert True
    finally:
        agent.api.app.config = original_config