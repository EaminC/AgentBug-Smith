import sys
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import pytest

def test_gemini_cli_option():
    """
    Test that CLI includes Gemini as a platform choice.
    """
    # Instead of inspecting source, check the actual CLI command
    from mle.cli import new
    # Check if 'Gemini' is in the help text or options
    # We'll check the command's callback function instead
    import click
    # The new command is a Click Command, we need to check its callback
    # or the actual function that handles platform choices
    from mle.cli import create_new_project
    import inspect
    source = inspect.getsource(create_new_project)
    # Look for platform choices in the source
    assert "'Gemini'" in source or '"Gemini"' in source or "Gemini" in source, "Gemini should be a CLI platform choice"

def test_gemini_model_module_exists():
    """
    Test that the gemini.py module exists after the patch.
    """
    # Try to import the module; if it doesn't exist, let it raise ImportError.
    # In buggy code, mle.model.gemini does not exist.
    # In fixed code, it does.
    try:
        from mle.model import gemini
        # If we reach here, the module exists (fixed).
        # We'll assert True to pass.
        assert True
    except ImportError:
        # In buggy code, the import fails.
        # We'll assert False to fail the test.
        assert False, "mle.model.gemini module should exist"

def test_clean_json_string_import_in_coder():
    """
    Test that clean_json_string is imported in coder.py.
    """
    # Read the source file directly.
    with open("mle/agents/coder.py", "r") as f:
        source = f.read()
    # The patch changes the import from:
    #   from mle.utils import get_config, print_in_box
    # to:
    #   from mle.utils import get_config, print_in_box, clean_json_string
    # We'll check that 'clean_json_string' appears in the import statement.
    # The buggy code imports only get_config and print_in_box.
    assert 'clean_json_string' in source, "clean_json_string should be imported in fixed code"

def test_search_papers_with_code_int_conversion():
    """
    Test that search_papers_with_code converts k to int.
    The patch fixes: results = data['results'][:int(k)]
    This test verifies the fix works.
    """
    from mle.function.search import search_papers_with_code

    # Mock the requests.get call
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"title": "Paper 1", "url": "http://example.com/1", "paper": {"title": "Paper 1"}},
            {"title": "Paper 2", "url": "http://example.com/2", "paper": {"title": "Paper 2"}},
            {"title": "Paper 3", "url": "http://example.com/3", "paper": {"title": "Paper 3"}}
        ]
    }

    with patch('requests.get', return_value=mock_response):
        # Test with string k (as might come from Gemini function call)
        result = search_papers_with_code("test query", k="2")
        
        # The function returns a formatted string, not a list
        # Check that it contains the expected paper title
        assert "Paper 1" in result or "Paper 2" in result, f"Expected paper titles in result, got: {result}"

def test_gemini_model_initialization():
    """
    Test that GeminiModel can be initialized correctly.
    This test ensures the gemini.py module exists and can be instantiated.
    """
    # Skip this test if the gemini module doesn't exist (buggy state)
    try:
        from mle.model import gemini
    except ImportError:
        pytest.skip("mle.model.gemini module doesn't exist (buggy state)")
    
    # Mock the google.generativeai module to avoid actual API dependency
    mock_gemini = MagicMock()
    mock_gemini.protos = MagicMock()
    mock_gemini.protos.Type = MagicMock()
    mock_gemini.protos.Type.STRING = 1
    mock_gemini.protos.Type.OBJECT = 2
    mock_gemini.protos.Type.NUMBER = 3
    mock_gemini.protos.Type.BOOLEAN = 4
    mock_gemini.protos.Type.ARRAY = 5
    mock_gemini.protos.Type.TYPE_UNSPECIFIED = 0
    mock_gemini.protos.Tool = MagicMock()
    mock_gemini.protos.FunctionDeclaration = MagicMock()
    mock_gemini.protos.Schema = MagicMock()
    mock_gemini.protos.Part = MagicMock()
    mock_gemini.protos.FunctionResponse = MagicMock()
    mock_gemini.protos.Content = MagicMock()
    mock_gemini.types = MagicMock()
    mock_gemini.types.GenerationConfig = MagicMock()
    mock_gemini.GenerativeModel = MagicMock()
    mock_gemini.configure = MagicMock()

    # Mock importlib.util.find_spec to return a spec
    with patch('importlib.util.find_spec', return_value=MagicMock()):
        with patch.dict('sys.modules', {'google.generativeai': mock_gemini}):
            # Import after patching
            from mle.model.gemini import GeminiModel
            # Instantiate with dummy API key
            model = GeminiModel(api_key='fake-key', model='gemini-1.5-flash')
            assert model.model_type == 'Gemini'
            assert model.model == 'gemini-1.5-flash'

def test_gemini_model_load_model():
    """
    Test that load_model can load GeminiModel when platform is 'Gemini'.
    """
    # Skip if gemini module doesn't exist
    try:
        from mle.model import gemini
    except ImportError:
        pytest.skip("mle.model.gemini module doesn't exist (buggy state)")
    
    # Mock the google.generativeai module
    mock_gemini = MagicMock()
    mock_gemini.protos = MagicMock()
    mock_gemini.protos.Type = MagicMock()
    mock_gemini.protos.Type.STRING = 1
    mock_gemini.protos.Type.OBJECT = 2
    mock_gemini.protos.Type.NUMBER = 3
    mock_gemini.protos.Type.BOOLEAN = 4
    mock_gemini.protos.Type.ARRAY = 5
    mock_gemini.protos.Type.TYPE_UNSPECIFIED = 0
    mock_gemini.protos.Tool = MagicMock()
    mock_gemini.protos.FunctionDeclaration = MagicMock()
    mock_gemini.protos.Schema = MagicMock()
    mock_gemini.protos.Part = MagicMock()
    mock_gemini.protos.FunctionResponse = MagicMock()
    mock_gemini.protos.Content = MagicMock()
    mock_gemini.types = MagicMock()
    mock_gemini.types.GenerationConfig = MagicMock()
    mock_gemini.GenerativeModel = MagicMock()
    mock_gemini.configure = MagicMock()

    with patch.dict('sys.modules', {'google.generativeai': mock_gemini}):
        with patch('importlib.util.find_spec', return_value=MagicMock()):
            from mle.model import load_model
            from mle.utils import get_config
            
            # Create a mock config file to avoid None return
            mock_config = {
                'platform': 'Gemini',
                'api_key': 'fake-key',
                'model': 'gemini-1.5-flash'
            }
            
            # Mock get_config to return a valid config
            with patch('mle.utils.get_config', return_value=mock_config):
                model = load_model('/tmp', observable=False)
                # Verify the model is a GeminiModel
                assert model.model_type == 'Gemini'

def test_clean_json_string_usage_in_coder():
    """
    Test that clean_json_string is used in coder.py methods.
    """
    # Read the source file directly.
    with open("mle/agents/coder.py", "r") as f:
        source = f.read()
    # The patch replaces json.loads(text) with clean_json_string(text)
    # Check that clean_json_string appears in the code.
    assert 'clean_json_string(text)' in source or 'clean_json_string(' in source, "clean_json_string should be used in coder.py"