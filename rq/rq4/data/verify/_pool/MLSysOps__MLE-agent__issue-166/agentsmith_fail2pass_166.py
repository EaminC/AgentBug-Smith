import pytest

def test_gemini_model_import():
    """Test that GeminiModel can be imported from mle.model"""
    from mle.model import GeminiModel
    assert GeminiModel is not None

def test_gemini_constant_exists():
    """Test that MODEL_GEMINI constant is defined"""
    from mle.model import MODEL_GEMINI
    assert MODEL_GEMINI == 'Gemini'

def test_gemini_model_instantiation(mocker):
    """Test that GeminiModel can be instantiated with mocked google-generativeai dependency"""
    # Mock importlib to simulate google.generativeai being installed
    mock_gemini = mocker.MagicMock()
    mock_spec = mocker.MagicMock()
    
    mocker.patch('importlib.util.find_spec', return_value=mock_spec)
    mocker.patch('importlib.import_module', return_value=mock_gemini)
    
    from mle.model import GeminiModel
    
    # Instantiate the model
    model = GeminiModel(api_key='fake_api_key', model='gemini-1.5-flash', temperature=0.5)
    
    # Verify attributes are set correctly
    assert model.model == 'gemini-1.5-flash'
    assert model.model_type == 'Gemini'
    assert model.temperature == 0.5
    
    # Verify configure was called with the API key
    mock_gemini.configure.assert_called_once_with(api_key='fake_api_key')
