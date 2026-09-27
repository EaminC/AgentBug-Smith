import sys
from unittest.mock import MagicMock, patch

# Mock huggingface_hub to prevent ImportError for ModelFilter which may not exist
# in the installed version, avoiding import chain errors when loading SearchAgent
sys.modules['huggingface_hub'] = MagicMock()

from agent.function.search_agent import SearchAgent


def test_search_agent_handles_missing_search_engine_config():
    """
    Test that SearchAgent handles missing 'search_engine' key in config gracefully.
    
    Regression test for issue #56: KeyError: 'search_engine' not in the config.
    When enable_web_search=True but config lacks 'search_engine', it should not crash.
    """
    # Simulate a config dictionary missing the 'search_engine' key
    mock_config_dict = {
        'general': {
            'platform': 'openai'
            # 'search_engine' is intentionally omitted to reproduce the bug
        }
    }
    
    # Patch the config.read() method to return our mock config
    with patch('agent.function.search_agent.config.read', return_value=mock_config_dict):
        # Buggy code raises: KeyError: 'search_engine'
        # Fixed code uses .get() and handles None gracefully
        agent = SearchAgent(enable_web_search=True)
        
        # In the fixed version, engine_name should be None (from .get() returning None)
        # and the agent should have returned early without crashing
        assert agent.engine_name is None
