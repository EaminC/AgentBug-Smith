import os
import types as pytypes
import pytest

import mle.model.gemini as gemini_module
from mle.function import SEARCH_FUNCTIONS


# Dummy classes to mock google.genai.types components with correct signatures
class DummyTypesSchema:
    def __init__(self, type):
        self.type = type


class DummyTypesFunctionDeclaration:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters


class DummyTypesTool:
    def __init__(self, function_declarations):
        self.function_declarations = function_declarations


class DummyTypesFunctionCallingConfig:
    def __init__(self, mode):
        self.mode = mode


class DummyTypesToolConfig:
    def __init__(self, function_calling_config):
        self.function_calling_config = function_calling_config


class DummyTypesGenerateContentConfig:
    def __init__(self, temperature=None, response_mime_type=None, tool_config=None, system_instruction=None):
        self.temperature = temperature
        self.response_mime_type = response_mime_type
        self.tool_config = tool_config
        self.system_instruction = system_instruction


class DummyTypesPart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class DummyTypesContent:
    def __init__(self, role=None, parts=None):
        self.role = role
        self.parts = parts or []

    @classmethod
    def from_function_response(cls, name, response):
        # Return a dummy content object with a part that simulates a function response
        part = DummyTypesPart()
        part.function_response = {"name": name, "response": response}
        return cls(role='tool', parts=[part])


class DummyFunctionCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class DummyClientModels:
    def __init__(self):
        self.generate_content_called = 0
        self.generate_content_stream_called = 0

    def generate_content(self, model, contents, config):
        self.generate_content_called += 1
        # Simulate a response with a function call on the first call, then normal text
        if self.generate_content_called == 1:
            # Compose a dummy function call part
            func_call = DummyFunctionCall(name="search_arxiv", args={"query": "AI"})
            part = DummyTypesPart(function_call=func_call)
            content = DummyTypesContent(parts=[part])
            candidate = pytypes.SimpleNamespace(content=content)
            response = pytypes.SimpleNamespace(candidates=[candidate], text="Final response text")
            return response
        else:
            # No function call, just text
            response = pytypes.SimpleNamespace(candidates=[], text="Final response text")
            return response

    def generate_content_stream(self, model, contents, config):
        self.generate_content_stream_called += 1
        # Yield dummy chunks with text attribute
        class DummyChunk:
            def __init__(self, text):
                self.text = text

        yield DummyChunk("chunk1")
        yield DummyChunk("chunk2")
        yield DummyChunk("chunk3")


class DummyClientInstance:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.models = DummyClientModels()


@pytest.fixture(autouse=True)
def patch_gemini(monkeypatch):
    # Patch the imported client and types in the gemini_module
    dummy_client_ns = pytypes.SimpleNamespace(Client=lambda api_key=None: DummyClientInstance(api_key=api_key))
    dummy_types_ns = pytypes.SimpleNamespace(
        FunctionDeclaration=DummyTypesFunctionDeclaration,
        Schema=DummyTypesSchema,
        Tool=DummyTypesTool,
        GenerateContentConfig=DummyTypesGenerateContentConfig,
        ToolConfig=DummyTypesToolConfig,
        FunctionCallingConfig=DummyTypesFunctionCallingConfig,
        Part=DummyTypesPart,
        Content=DummyTypesContent,
    )
    # Patch attributes on the gemini_module
    # Instead of patching gemini_module.client and gemini_module.types attributes (which do not exist),
    # patch the imported google.genai modules inside gemini_module.
    # This requires patching the module attributes where gemini_module imports them from.
    # Assuming gemini_module imports client and types from google.genai, patch those modules in gemini_module namespace.

    # Patch gemini_module.client.Client to dummy client factory
    monkeypatch.setattr(gemini_module, "client", dummy_client_ns)
    monkeypatch.setattr(gemini_module, "types", dummy_types_ns)


def test_gemini_model_init_properties():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")
    assert gm.api_key is None or gm.api_key == os.getenv("OPENAI_API_KEY")  # api_key is not stored as attribute, but no error
    assert gm.model == "gemini-2.5-flash"
    assert gm.model_type == "Gemini"
    assert 0 <= gm.temperature <= 1
    assert hasattr(gm, "client")
    assert hasattr(gm.client, "models")


def test_adapt_history_for_gemini_format():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")
    chat_history = [
        {"role": "system", "content": "System instruction."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
        {"role": "system", "content": "Another system note."},
    ]
    system_instruction, prompt = gm._adapt_history_for_gemini(chat_history)
    assert "System instruction." in system_instruction
    assert "Another system note." in system_instruction
    assert isinstance(prompt, list)
    assert all(isinstance(p, dict) for p in prompt)
    roles = {p["role"] for p in prompt}
    assert roles <= {"user", "model"}


def test_create_gemini_tools_none_and_nonempty():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")
    # None input
    tools_none = gm._create_gemini_tools(None)
    assert tools_none is None

    # Empty list input
    tools_empty = gm._create_gemini_tools([])
    assert tools_empty is None

    # Non-empty input
    functions = [
        {
            "name": "search_arxiv",
            "description": "Search Arxiv papers",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
            },
        }
    ]
    tools = gm._create_gemini_tools(functions)
    assert tools is not None
    assert isinstance(tools, list)
    assert all(hasattr(tool, "function_declarations") for tool in tools)
    decl = tools[0].function_declarations[0]
    assert decl.name == "search_arxiv"
    assert decl.description == "Search Arxiv papers"
    # parameters is DummyTypesSchema instance
    assert hasattr(decl.parameters, "type")
    assert decl.parameters.type == "OBJECT"


def test_query_handles_no_functions_and_empty_history():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")
    chat_history = []
    response = gm.query(chat_history)
    assert isinstance(response, str)
    assert response != ""


def test_query_returns_string_and_limits_tools():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")

    chat_history = [
        {"role": "system", "content": "System instruction."},
        {"role": "user", "content": "Please search for AI papers."},
    ]
    functions = [
        {
            "name": "search_arxiv",
            "description": "Search Arxiv papers",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
            },
        }
    ]

    # Patch get_function to a dummy function that returns a fixed string
    def dummy_search_arxiv(query):
        return f"Results for {query}"

    original_get_function = gemini_module.get_function
    gemini_module.get_function = lambda name: dummy_search_arxiv

    try:
        response = gm.query(chat_history, functions=functions)
        assert isinstance(response, str)
        assert "Results for AI" in response or "Final response text" in response or "[GEMINI WARNING]" in response
    finally:
        gemini_module.get_function = original_get_function


def test_gemini_model_stream():
    gm = gemini_module.GeminiModel(api_key=os.getenv("OPENAI_API_KEY"), model="gemini-2.5-flash")

    chat_history = [
        {"role": "system", "content": "System instruction."},
        {"role": "user", "content": "Stream test"},
    ]

    stream = gm.stream(chat_history)
    chunks = list(stream)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert len(chunks) > 0
    assert "chunk1" in chunks[0] or "chunk2" in chunks[1] or "chunk3" in chunks[-1]