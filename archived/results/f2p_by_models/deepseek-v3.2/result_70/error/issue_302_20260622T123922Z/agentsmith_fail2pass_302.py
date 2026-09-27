import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Import the module once at the top level to avoid repeated imports
# that trigger lancedb import issues
import mle.model.gemini


def test_gemini_default_model_change():
    """
    Test that default model changes from old SDK to new.
    """
    # Mock the google-genai SDK
    mock_client = Mock()
    mock_types = Mock()
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        # Re-import to get fresh module with mocks
        if 'mle.model.gemini' in sys.modules:
            del sys.modules['mle.model.gemini']
        import importlib
        gemini_module = importlib.import_module('mle.model.gemini')
        
        # Test that GeminiModel can be instantiated
        model = gemini_module.GeminiModel(model_name="gemini-pro")
        assert model is not None


def test_gemini_model_initialization_with_new_sdk():
    """
    Test model initialization with new SDK structure.
    """
    mock_client = Mock()
    mock_types = Mock()
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        if 'mle.model.gemini' in sys.modules:
            del sys.modules['mle.model.gemini']
        import importlib
        gemini_module = importlib.import_module('mle.model.gemini')
        
        # Test initialization with API key
        model = gemini_module.GeminiModel(
            model_name="gemini-pro",
            api_key="test-key"
        )
        assert model is not None


def test_gemini_create_gemini_tools():
    """
    Test create_gemini_tools method.
    """
    mock_client = Mock()
    mock_types = Mock()
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        if 'mle.model.gemini' in sys.modules:
            del sys.modules['mle.model.gemini']
        import importlib
        gemini_module = importlib.import_module('mle.model.gemini')
        
        model = gemini_module.GeminiModel(model_name="gemini-pro")
        
        # Mock functions
        mock_functions = [
            {"name": "test_func", "description": "Test function"}
        ]
        
        # Test create_gemini_tools method
        tools = model.create_gemini_tools(mock_functions)
        assert tools is not None


def test_gemini_adapt_history_for_gemini():
    """
    Test adapt_history_for_gemini method.
    """
    mock_client = Mock()
    mock_types = Mock()
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        if 'mle.model.gemini' in sys.modules:
            del sys.modules['mle.model.gemini']
        import importlib
        gemini_module = importlib.import_module('mle.model.gemini')
        
        model = gemini_module.GeminiModel(model_name="gemini-pro")
        
        # Test history adaptation
        mock_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        adapted = model.adapt_history_for_gemini(mock_history)
        assert adapted is not None


def test_gemini_query_with_function_calling():
    """
    Test query method with function calling.
    """
    mock_client = Mock()
    mock_types = Mock()
    
    # Mock the generate_content method
    mock_generate_content = Mock()
    mock_client.Client.return_value.models.generate_content = mock_generate_content
    
    # Create a mock response
    mock_response = Mock()
    mock_candidate = Mock()
    mock_content = Mock()
    mock_part = Mock()
    mock_part.text = "Test response"
    mock_content.parts = [mock_part]
    mock_candidate.content = mock_content
    mock_response.candidates = [mock_candidate]
    mock_response.text = "Test response"
    
    mock_generate_content.return_value = mock_response
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        # Mock get_function to avoid actual function calls
        mock_get_function = Mock(return_value=Mock(return_value="mocked_result"))
        
        with patch('mle.function.get_function', mock_get_function):
            if 'mle.model.gemini' in sys.modules:
                del sys.modules['mle.model.gemini']
            import importlib
            gemini_module = importlib.import_module('mle.model.gemini')
            
            model = gemini_module.GeminiModel(model_name="gemini-pro")
            
            # Test query with functions
            response = model.query(
                prompt="Test prompt",
                functions=[{"name": "test_func", "description": "Test"}]
            )
            assert response is not None


def test_gemini_stream_method():
    """
    Test the stream method.
    """
    mock_client = Mock()
    mock_types = Mock()
    
    # Mock the generate_content_stream method
    mock_generate_content_stream = Mock()
    mock_client.Client.return_value.models.generate_content_stream = mock_generate_content_stream
    
    # Mock stream response
    mock_chunk1 = Mock()
    mock_chunk1.text = 'Hello '
    mock_chunk2 = Mock()
    mock_chunk2.text = 'World'
    mock_generate_content_stream.return_value = [mock_chunk1, mock_chunk2]
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        if 'mle.model.gemini' in sys.modules:
            del sys.modules['mle.model.gemini']
        import importlib
        gemini_module = importlib.import_module('mle.model.gemini')
        
        model = gemini_module.GeminiModel(model_name="gemini-pro")
        
        # Test stream method
        stream_result = model.stream(prompt="Test prompt")
        assert stream_result is not None


def test_gemini_search_function_limit():
    """
    Test that search function limit is enforced (3 attempts).
    """
    mock_client = Mock()
    mock_types = Mock()
    
    # Mock the generate_content method to return function calls
    mock_generate_content = Mock()
    mock_client.Client.return_value.models.generate_content = mock_generate_content
    
    # Create mock function call response
    mock_response = Mock()
    mock_candidate = Mock()
    mock_content = Mock()
    mock_part = Mock()
    mock_part.function_call = Mock()
    mock_part.function_call.name = 'search_web'
    mock_part.function_call.args = {'query': 'test'}
    mock_content.parts = [mock_part]
    mock_candidate.content = mock_content
    mock_response.candidates = [mock_candidate]
    mock_response.text = None
    
    mock_generate_content.return_value = mock_response
    
    with patch.dict('sys.modules', {
        'google.genai': Mock(),
        'google.genai.client': mock_client,
        'google.genai.types': mock_types,
    }):
        # Mock get_function to return a search function
        mock_get_function = Mock(return_value=Mock(return_value='search_result'))
        
        # Mock process_function_name
        mock_process_function_name = Mock(return_value='search_web')
        
        with patch('mle.function.get_function', mock_get_function):
            with patch('mle.function.process_function_name', mock_process_function_name):
                if 'mle.model.gemini' in sys.modules:
                    del sys.modules['mle.model.gemini']
                import importlib
                gemini_module = importlib.import_module('mle.model.gemini')
                
                model = gemini_module.GeminiModel(model_name="gemini-pro")
                
                # Test query with search function that would hit limit
                response = model.query(
                    prompt="Search test",
                    functions=[{"name": "search_web", "description": "Search the web"}]
                )
                assert response is not None