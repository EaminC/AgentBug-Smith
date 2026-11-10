import builtins
import types
import pytest

import openai
from ai import AI


class DummyInvalidRequestError(Exception):
    pass


class DummyModel:
    @staticmethod
    def retrieve(name):
        if name == "gpt-4":
            raise DummyInvalidRequestError("Model not available")
        return {"id": name}


def test_ai_model_fallback(monkeypatch):
    # Patch openai.Model.retrieve to our dummy method that raises for gpt-4
    monkeypatch.setattr(openai.Model, "retrieve", DummyModel.retrieve)

    # Patch openai.error.InvalidRequestError to our dummy exception class
    # openai.error may not exist, so patch openai.error via sys.modules trick
    import sys

    if not hasattr(openai, "error"):
        error_module = types.SimpleNamespace(InvalidRequestError=DummyInvalidRequestError)
        sys.modules["openai.error"] = error_module
        setattr(openai, "error", error_module)
    else:
        # Patch the existing error.InvalidRequestError to DummyInvalidRequestError
        monkeypatch.setattr(openai.error, "InvalidRequestError", DummyInvalidRequestError)

    # Create AI instance, which should fallback to gpt-3.5-turbo due to dummy retrieve raising
    ai_instance = AI()

    # The model should be set to gpt-3.5-turbo in kwargs after fallback
    assert ai_instance.kwargs.get("model") == "gpt-3.5-turbo"


class DummyChatCompletion:
    @staticmethod
    def create(*args, **kwargs):
        # Return a dummy streaming response generator
        class DummyStream:
            def __iter__(self_inner):
                yield {"choices": [{"delta": {"content": "Hello"}}]}
                yield {"choices": [{"delta": {"content": " world"}}]}
                yield {"choices": [{"delta": {}}]}

        return DummyStream()


def test_ai_start_and_next_basic(monkeypatch):
    # Patch openai.ChatCompletion.create to dummy streaming response
    monkeypatch.setattr(openai.ChatCompletion, "create", DummyChatCompletion.create)

    # Patch openai.Model.retrieve to dummy that does not raise
    monkeypatch.setattr(openai.Model, "retrieve", lambda name: {"id": name})

    # Patch openai.error.InvalidRequestError to a dummy exception class if needed
    import sys
    import types

    if not hasattr(openai, "error"):
        error_module = types.SimpleNamespace(InvalidRequestError=Exception)
        sys.modules["openai.error"] = error_module
        setattr(openai, "error", error_module)

    ai = AI(model="gpt-3.5-turbo")

    system_msg = "You are a helpful assistant."
    user_msg = "Hello, AI!"
    messages = ai.start(system_msg, user_msg)

    # The returned messages should include the system and user messages plus assistant reply
    assert isinstance(messages, list)
    assert any(m.get("role") == "assistant" for m in messages)
    assistant_msg = next(m for m in messages if m.get("role") == "assistant")
    assert "Hello world" in assistant_msg.get("content", "")

    # Test next() with additional prompt
    new_messages = ai.next(messages, prompt="Continue")
    assert isinstance(new_messages, list)
    assert any(m.get("role") == "assistant" for m in new_messages)
    new_assistant_msg = next(m for m in new_messages if m.get("role") == "assistant")
    assert "Hello world" in new_assistant_msg.get("content", "")
