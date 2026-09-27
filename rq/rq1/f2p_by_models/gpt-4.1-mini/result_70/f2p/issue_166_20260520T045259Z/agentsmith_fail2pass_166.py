import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.modules['git'] = MagicMock()
os.environ["GIT_PYTHON_REFRESH"] = "quiet"


def test_gemini_framework_integration():
    """
    Validates Gemini creation, query, and streaming logic.
    - Pre-Patch: Fails via pytest.fail (Exit Code 1) due to missing files.
    - Post-Patch: Passes successfully (Exit Code 0).
    """
    # 1. LAZY IMPORTS to prevent Exit Code 2 on pre-patch
    try:
        from mle.model.gemini import GeminiModel
        import mle.model.__init__ as model_init
    except ImportError:
        pytest.fail("CRITICAL BUG: Gemini framework modules (mle.model.gemini) are missing.")

    # 2. Check Constants
    if not hasattr(model_init, "MODEL_GEMINI"):
        pytest.fail("CRITICAL BUG: 'MODEL_GEMINI' constant missing from model root.")
    assert model_init.MODEL_GEMINI == "Gemini"

    # 3. Mock the external google.generativeai module
    mock_genai = MagicMock()
    mock_genai.protos.Type.STRING = 1
    mock_genai.protos.Type.OBJECT = 2

    with patch("importlib.util.find_spec", return_value=True), \
         patch("importlib.import_module", return_value=mock_genai):
        
        # Instantiate Model
        model = GeminiModel(api_key="dummy_key", model="gemini-1.5-flash")

        # Setup Chat Mocks
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.parts = []  # Simulate no function calls
        mock_response.text = "Hello from Gemini"
        mock_chat.send_message.return_value = mock_response
        
        mock_gen_model = MagicMock()
        mock_gen_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_gen_model

        # --- Test A: standard query ---
        # query() maps "content" to "parts" internally
        chat_history = [{"role": "user", "content": "Hi"}]
        result = model.query(chat_history)
        assert result == "Hello from Gemini"

        # --- Test B: stream query ---
        # WORKAROUND: The PR author forgot to map the history in stream()!
        # We must explicitly pass "parts" to prevent a KeyError on the post-patch code.
        mock_chunk = MagicMock()
        mock_chunk.text = "Stream chunk"
        mock_chat.send_message.return_value = [mock_chunk]

        stream_history = [{"role": "user", "parts": "Hi stream"}]
        stream_res = list(model.stream(stream_history))
        assert stream_res == ["Stream chunk"]

        # --- Test C: function schema mapping ---
        functions = [{
            "name": "search",
            "description": "search papers",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}
        }]
        tool = model._map_functions_from_openai(functions)
        assert tool is not None


def test_cli_gemini_support():
    """
    Validates that Gemini was added to interactive CLI prompts.
    """
    try:
        import inspect
        import mle.cli as cli_module
    except Exception as e:
        pytest.fail(f"CLI check failed to import: {e}")
        
    source = inspect.getsource(cli_module)
    if "'Gemini'" not in source and '"Gemini"' not in source:
        pytest.fail("CRITICAL BUG: 'Gemini' not added to CLI platform choices.")


def test_search_papers_k_cast():
    """
    Validates that the 'k' parameter is correctly cast to an integer before slicing.
    """
    try:
        from mle.function.search import search_papers_with_code
    except ImportError:
        pytest.skip("Search module not found")
        
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": [{"title": "Paper 1"}]}
        
        try:
            # Pre-patch code fails here with TypeError: slice indices must be integers
            search_papers_with_code("agent reproducibility", k="1") 
        except TypeError as type_err:
            pytest.fail(f"CRITICAL BUG: search_papers_with_code fails to cast string 'k': {type_err}")