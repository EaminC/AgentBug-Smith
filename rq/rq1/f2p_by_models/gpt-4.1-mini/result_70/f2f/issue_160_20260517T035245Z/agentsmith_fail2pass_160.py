import os
import pytest

import mle.agents.coder as coder_module
import mle.model as model_module


def test_coder_generate_code():
    """
    Test that the Coder agent generates code and includes capabilities in the system prompt.
    This test should fail on buggy codebase (missing Coder class or incomplete prompt),
    and pass after the fix.
    """
    # Check that coder_module is importable and has Coder class
    assert coder_module is not None, "mle.agents.coder module must be importable"
    assert hasattr(coder_module, "Coder"), "coder_module must have Coder class"

    # Instantiate Coder and check sys_prompt contains the fixed phrase
    coder = coder_module.Coder(model=None, working_dir="testdir")
    assert "Your can leverage your capabilities" in coder.sys_prompt


def test_coder_sys_prompt_contains_capabilities():
    """
    Test that the Coder sys_prompt contains the phrase 'Your can leverage your capabilities'
    after patch, indicating the fix is applied.
    Should fail on buggy codebase (missing or incomplete prompt),
    and pass after the fix.
    """
    assert coder_module is not None, "mle.agents.coder module must be importable"
    assert hasattr(coder_module, "Coder"), "coder_module must have Coder class"

    coder = coder_module.Coder(model=None, working_dir=".")
    # The fixed patch adds this phrase exactly
    assert "Your can leverage your capabilities" in coder.sys_prompt


class DummyClaudeClient:
    """
    Dummy Claude client to simulate messages.create returning a tool_use completion,
    then a normal completion.
    """

    def __init__(self):
        self.call_count = 0

    class DummyCompletion:
        def __init__(self, stop_reason, content):
            self.stop_reason = stop_reason
            self.content = content

    @property
    def messages(self):
        # This is a property to allow messages.create and messages.stream
        return self

    def create(self, *, max_tokens, model, system, messages, temperature, stream=False, tools=None):
        self.call_count += 1
        # On first call, simulate a tool_use response
        if self.call_count == 1:
            # content is a list of tool_use objects
            tool_use_obj = type(
                "ToolUse",
                (),
                {
                    "type": "tool_use",
                    "id": "123",
                    "name": "dummy_function",
                    "input": {"arg1": "value1"},
                },
            )()
            return self.DummyCompletion(stop_reason="tool_use", content=[tool_use_obj])
        else:
            # On second call, return normal text content
            class TextContent:
                def __init__(self, text):
                    self.text = "dummy_function result"

            return self.DummyCompletion(stop_reason=None, content=[TextContent("dummy_function result")])

    def stream(self, *args, **kwargs):
        # Not used in tests here
        pass


def dummy_function(**kwargs):
    return "dummy_function"


def test_claude_query_tool_use(monkeypatch):
    """
    Test that the ClaudeModel correctly handles tool_use completions by calling the function
    and returning the final response. This tests the recursive tool call handling logic.
    Should fail on buggy codebase (e.g. AttributeError or missing tool call handling),
    and pass after the fix.
    """
    # Find the ClaudeModel or ModelClaude class in model_module
    claude_cls = None
    if hasattr(model_module, "ClaudeModel"):
        claude_cls = model_module.ClaudeModel
    elif hasattr(model_module, "ModelClaude"):
        claude_cls = model_module.ModelClaude
    else:
        pytest.skip("ClaudeModel or ModelClaude class not found in model_module")

    # Patch ClaudeModel.__init__ to avoid real client creation and use DummyClaudeClient
    def dummy_init(self, api_key, model=None, temperature=0.7):
        self.anthropic = None
        self.model_type = model_module.MODEL_CLAUDE
        self.temperature = temperature
        self.client = DummyClaudeClient()
        self.model = "dummy-claude-model"
        self.func_call_history = []

    monkeypatch.setattr(claude_cls, "__init__", dummy_init)

    claude = claude_cls(api_key=os.getenv("OPENAI_API_KEY", "dummy"))

    # Patch get_function to return dummy_function for any function name
    monkeypatch.setattr(model_module, "get_function", lambda name: dummy_function)
    # Patch process_function_name to identity function
    monkeypatch.setattr(model_module, "process_function_name", lambda name: name)

    chat_history = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Run tool"},
    ]

    # Call query with functions and response_format to trigger tool_use handling
    response = claude.query(
        chat_history,
        functions=[{"name": "dummy_function"}],
        response_format={"type": "json"},
    )

    # The response should be a string returned by dummy_function after recursive calls
    assert isinstance(response, str)
    # It should contain the dummy_function result string
    assert "dummy_function" in response


def test_coder_create_file_and_directory_methods():
    """
    Test that the Coder agent has create_file and create_directory methods,
    which are mentioned in the sys_prompt capabilities.
    """
    assert coder_module is not None, "mle.agents.coder module must be importable"
    assert hasattr(coder_module, "Coder"), "coder_module must have Coder class"

    coder = coder_module.Coder(model=None, working_dir=".")
    # The patch mentions these functions in the prompt, so they should exist as methods
    assert hasattr(coder, "create_file"), "Coder must have create_file method"
    assert hasattr(coder, "create_directory"), "Coder must have create_directory method"


def test_model_default_model_name():
    """
    Test that the default model name for OpenAI is set to 'gpt-4o-2024-08-06' after patch.
    Should fail on buggy codebase (default 'gpt-4o'), pass after fix.
    """
    # Instantiate Model with no model argument
    # Use environment variable for api_key
    api_key = os.getenv("OPENAI_API_KEY", "dummy")

    # Model is abstract, so instantiate a concrete subclass if available
    # Try to find a concrete subclass of Model in model_module
    ModelClass = None
    # Prefer a concrete subclass named OpenAIModel or similar if exists
    for candidate_name in ["OpenAIModel", "ModelOpenAI", "Model"]:
        cls = getattr(model_module, candidate_name, None)
        if cls is not None:
            # Check if cls is not abstract by checking for abstract methods
            if not hasattr(cls, "__abstractmethods__") or len(cls.__abstractmethods__) == 0:
                ModelClass = cls
                break
    if ModelClass is None:
        # fallback to Model if it can be instantiated (unlikely)
        ModelClass = model_module.Model

    # If ModelClass is still abstract, skip test
    try:
        model = ModelClass(api_key=api_key)
    except TypeError:
        pytest.skip("No concrete Model class available for instantiation")

    assert model.model == "gpt-4o-2024-08-06"


def test_debugger_sys_prompt_contains_capabilities():
    """
    Test that the Debugger agent sys_prompt contains the phrase 'Your can leverage your capabilities'
    after patch, indicating the fix is applied.
    """
    debugger_cls = getattr(model_module, "Debugger", None)
    if debugger_cls is None:
        # fallback to import from agents.debugger if Debugger class not in model_module
        import mle.agents.debugger as debugger_module

        debugger_cls = getattr(debugger_module, "Debugger", None)
    if debugger_cls is None:
        pytest.skip("Debugger class not found")

    debugger = debugger_cls(model=None)
    assert "Your can leverage your capabilities" in debugger.sys_prompt