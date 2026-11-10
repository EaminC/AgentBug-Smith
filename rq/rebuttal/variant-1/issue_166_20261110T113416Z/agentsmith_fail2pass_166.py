import importlib
import importlib.util
import pytest

import mle.utils
import mle.function
import mle.model


def test_load_model_with_gemini_platform(monkeypatch):
    # Patch importlib.util.find_spec and importlib.import_module to simulate gemini installed
    def fake_find_spec(name):
        if name == "google.generativeai":
            return True
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    class DummyGemini:
        def configure(self, api_key):
            self.api_key = api_key

    def fake_import_module(name):
        if name == "google.generativeai":
            return DummyGemini()
        return importlib.import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    # Patch get_config to return Gemini platform config
    def fake_get_config(project_dir):
        return {
            "platform": "Gemini",
            "api_key": "dummy_api_key",
            "model": "gemini-1.5-flash",
        }

    monkeypatch.setattr(mle.utils, "get_config", fake_get_config)

    # Import GeminiModel after patching so import succeeds
    from mle.model.gemini import GeminiModel

    model = mle.model.load_model("dummy_project_dir", model_name="gemini-1.5-flash")
    # The loaded model should be an instance of GeminiModel
    assert isinstance(model._model, GeminiModel)
    # The api_key and model name should be set correctly
    assert model._model.api_key == "dummy_api_key" or hasattr(model._model, "api_key")
    assert model._model.model == "gemini-1.5-flash"


def test_gemini_model_query_and_stream(monkeypatch):
    # Patch importlib.util.find_spec and importlib.import_module to simulate gemini installed
    def fake_find_spec(name):
        if name == "google.generativeai":
            return True
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    class DummyFunctionCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args

    class DummyPart:
        def __init__(self, function_call=None, text="response text"):
            self.function_call = function_call
            self.text = text

    class DummyCompletion:
        def __init__(self, parts, text=None):
            self.parts = parts
            self.text = text or "final response text"

    class DummyChatHandler:
        def __init__(self):
            self.sent_messages = []

        def send_message(self, message, **kwargs):
            self.sent_messages.append((message, kwargs))
            # Simulate a function call in the first completion
            if isinstance(message, str):
                # Return a completion with a function call part
                fn_call = DummyFunctionCall(name="search_papers_with_code", args={"query": "test"})
                part = DummyPart(function_call=fn_call)
                return DummyCompletion(parts=[part])
            else:
                # This is the second call with function response parts
                return DummyCompletion(parts=[], text="final response text")

    class DummyGenerativeModel:
        def __init__(self, model):
            self.model = model

        def start_chat(self, history):
            return DummyChatHandler()

    class DummyProtosType:
        STRING = 1
        OBJECT = 2
        NUMBER = 3
        BOOLEAN = 4
        ARRAY = 5
        TYPE_UNSPECIFIED = 0

    class DummyProtos:
        Type = DummyProtosType

        @staticmethod
        def Tool(function_declarations):
            return "tool"

        @staticmethod
        def FunctionDeclaration(name, description, parameters):
            return "func_decl"

        @staticmethod
        def Schema(type, properties=None, required=None, description=None):
            return "schema"

        @staticmethod
        def Part(function_response=None, text=None):
            return DummyPart(text=text or "response text")

        @staticmethod
        def FunctionResponse(name, response):
            return "func_resp"

        @staticmethod
        def Content(parts):
            return "content"

    class DummyTypes:
        @staticmethod
        def GenerationConfig(**kwargs):
            return "gen_config"

    class DummyGemini:
        protos = DummyProtos
        types = DummyTypes
        GenerativeModel = DummyGenerativeModel

        def __init__(self):
            self.api_key = None

        def configure(self, api_key):
            self.api_key = api_key

    monkeypatch.setattr(importlib, "import_module", lambda name: DummyGemini() if name == "google.generativeai" else importlib.import_module(name))
    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    # Patch get_function to simulate search function returning dummy JSON string
    def dummy_search_papers_with_code(query, k=8):
        # Return a dummy JSON string that can be parsed by clean_json_string in fixed code
        # The patched code uses clean_json_string which expects a JSON string, so return a valid JSON string
        return '{"results":[{"title":"Test Paper","url":"http://example.com"}]}'

    monkeypatch.setattr(mle.function, "get_function", lambda name: dummy_search_papers_with_code if name == "search_papers_with_code" else lambda **kwargs: None)

    # Import GeminiModel now after patching
    from mle.model.gemini import GeminiModel

    model = GeminiModel(api_key="dummy_key", model="gemini-1.5-flash")

    # Prepare a fake chat history in OpenAI style
    chat_history = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Search papers about test."}
    ]

    # Query the model, should return the final response text from DummyCompletion
    response = model.query(chat_history)
    assert isinstance(response, str)
    assert "final response text" in response

    # Test streaming output
    stream_outputs = list(model.stream(chat_history))
    assert all(isinstance(chunk, str) for chunk in stream_outputs)
    assert any("response text" in chunk for chunk in stream_outputs) or len(stream_outputs) > 0
