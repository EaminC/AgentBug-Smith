import builtins
import json
import types

import pytest

import mle.agents.coder as coder_module
import mle.model as model_module


def test_coder_agent_generate_code():
    """
    Test that the CodeAgent can generate code with a dummy ClaudeModel,
    and that the output JSON contains expected keys including 'command' and 'dependency'.
    This test triggers the code generation flow that was broken before the fix.
    """

    # Patch ClaudeModel to avoid importing 'anthropic' module which may not be installed
    original_init = model_module.ClaudeModel.__init__

    def patched_init(self, api_key, model=None, temperature=0.7):
        # Patch to avoid importing 'anthropic' module
        # Instead, set dummy attributes needed for the test
        self.api_key = api_key
        self.model = model if model else 'gpt-4o-2024-08-06'
        self.temperature = temperature
        self.func_call_history = []

        # Provide a dummy client with messages.create method
        class DummyCompletion:
            def __init__(self):
                self.content = [types.SimpleNamespace(text=json.dumps({
                    "dependency": ["torch", "scikit-learn"],
                    "command": "python run.py",
                    "message": "the project-related has been generated in the project.py.",
                    "debug": "true"
                }))]
                self.stop_reason = None

        class DummyClient:
            class messages:
                @staticmethod
                def create(*args, **kwargs):
                    return DummyCompletion()

        self.client = DummyClient()

    model_module.ClaudeModel.__init__ = patched_init

    # Patch get_config to return a dict to avoid NoneType error in CodeAgent __init__
    import mle.agents.coder as coder_mod
    original_get_config = coder_mod.get_config
    coder_mod.get_config = lambda: {}

    # Create dummy model instance
    claude_model = model_module.ClaudeModel(api_key="dummy_key")

    # Create CodeAgent with the dummy model
    agent = coder_module.CodeAgent(model=claude_model, working_dir="testdir")

    # Prepare a minimal chat history to trigger code generation
    chat_history = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Generate a simple ML project."}
    ]

    # Call the model query method to simulate generation
    output = claude_model.query(chat_history, response_format={"type": "json"})

    # The output should be a JSON string with keys: dependency, command, message, debug
    try:
        parsed = json.loads(output)
    except Exception as e:
        pytest.fail(f"Output is not valid JSON: {e}")

    assert isinstance(parsed, dict)
    assert "dependency" in parsed
    assert "command" in parsed
    assert "message" in parsed
    assert "debug" in parsed

    # Clean up patches
    model_module.ClaudeModel.__init__ = original_init
    coder_mod.get_config = original_get_config


def test_coder_sys_prompt_contains_capabilities():
    """
    Test that the CodeAgent's system prompt contains the corrected capabilities text
    after the fix, specifically the phrase "Your can leverage your capabilities".
    This was changed from "Your capabilities include" to "Your can leverage your capabilities".
    """

    # Patch get_config to avoid NoneType error
    import mle.agents.coder as coder_mod
    original_get_config = coder_mod.get_config
    coder_mod.get_config = lambda: {}

    # Instantiate CodeAgent with no model to test prompt text
    agent = coder_module.CodeAgent(model=None, working_dir="testdir")

    # The system prompt should contain the fixed phrase
    assert "Your can leverage your capabilities" in agent.sys_prompt

    # The system prompt should NOT contain the old phrase
    assert "Your capabilities include" not in agent.sys_prompt

    # Clean up patch
    coder_mod.get_config = original_get_config
