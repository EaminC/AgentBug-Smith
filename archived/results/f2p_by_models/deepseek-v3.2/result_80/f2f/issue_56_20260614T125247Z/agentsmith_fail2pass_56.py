import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try to import the required modules with error handling
try:
    from agent.utils.config import Config
    from agent.function.search_agent import SearchAgent
except ImportError as e:
    print(f"Import error: {e}")
    print("Trying alternative import paths...")
    # Try alternative import paths
    try:
        # If agent is a package in the current directory
        sys.path.insert(0, str(Path(__file__).parent))
        from utils.config import Config
        from function.search_agent import SearchAgent
    except ImportError as e2:
        print(f"Alternative import also failed: {e2}")
        raise

def test_search_agent_without_search_engine_config():
    """
    Test that SearchAgent does not raise KeyError when 'search_engine' is missing from config.
    In buggy code, config_dict['general']['search_engine'] raises KeyError.
    In fixed code, config_dict['general'].get('search_engine') returns None and handles it.
    """
    # Create a temporary directory for config file
    tmpdir = tempfile.mkdtemp()
    original_home = os.environ.get('HOME')
    os.environ['HOME'] = tmpdir
    try:
        # Write a config file that does NOT contain 'search_engine' in 'general' section
        config_content = """
[general]
some_other_key = value

[some_engine]
key = value
"""
        config_path = Path(tmpdir) / '.mle' / 'config.ini'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content)

        # Reload config to pick up the new file
        # Clear any existing instance
        if hasattr(Config, '_instance'):
            Config._instance = None
        
        config = Config()

        # Instantiate SearchAgent with enable_web_search=False (so it reads config)
        # In buggy code, this will raise KeyError: 'search_engine'
        # In fixed code, this should not raise KeyError and should set engine_name to None
        agent = SearchAgent(enable_web_search=False)

        # If we reach here without exception, the bug is fixed.
        # Additionally, we can assert that engine_name is None (or not set)
        # because the config lacks 'search_engine'.
        assert agent.engine_name is None or agent.engine_name == ''
        print("✓ test_search_agent_without_search_engine_config passed")
    except Exception as e:
        print(f"✗ test_search_agent_without_search_engine_config failed: {e}")
        raise
    finally:
        if original_home:
            os.environ['HOME'] = original_home
        else:
            del os.environ['HOME']
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_search_agent_with_search_engine_config():
    """
    Test that SearchAgent works correctly when 'search_engine' is present in config.
    """
    tmpdir = tempfile.mkdtemp()
    original_home = os.environ.get('HOME')
    os.environ['HOME'] = tmpdir
    try:
        # Write a config file that DOES contain 'search_engine' in 'general' section
        config_content = """
[general]
search_engine = test_engine

[test_engine]
api_key = dummy_key
"""
        config_path = Path(tmpdir) / '.mle' / 'config.ini'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content)

        # Clear config instance
        if hasattr(Config, '_instance'):
            Config._instance = None
            
        config = Config()

        agent = SearchAgent(enable_web_search=False)
        # engine_name should be 'test_engine'
        assert agent.engine_name == 'test_engine'
        print("✓ test_search_agent_with_search_engine_config passed")
    except Exception as e:
        print(f"✗ test_search_agent_with_search_engine_config failed: {e}")
        raise
    finally:
        if original_home:
            os.environ['HOME'] = original_home
        else:
            del os.environ['HOME']
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    # Run tests manually
    print("Running SearchAgent tests...")
    
    try:
        test_search_agent_without_search_engine_config()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
        
    try:
        test_search_agent_with_search_engine_config()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
        
    print("All tests passed successfully!")