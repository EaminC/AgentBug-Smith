import builtins
import pytest
from unittest.mock import patch, MagicMock
import ai


def test_ai_init_sets_model_to_gpt_35_turbo_when_gpt4_unavailable(capsys):
    # Patch openai.Model.retrieve to raise openai.error.InvalidRequestError to simulate gpt-4 unavailability
    # We must patch openai.error.InvalidRequestError to a dummy exception class because openai.error is missing in the environment
    class DummyInvalidRequestError(Exception):
        pass

    # Patch ai.openai.error.InvalidRequestError to DummyInvalidRequestError for the test
    with patch.object(ai.openai, "Model") as mock_model, \
         patch.object(ai.openai, "error", create=True) as mock_error:
        mock_error.InvalidRequestError = DummyInvalidRequestError

        def dummy_retrieve(model_name):
            if model_name == "gpt-4":
                raise DummyInvalidRequestError("Model not found")
            return MagicMock()

        mock_model.retrieve.side_effect = dummy_retrieve

        instance = ai.AI()
        out, _ = capsys.readouterr()
        # The print message in __init__ uses "reverting to gpt-3.5.turbo" (with dot) or "reverting to gpt-3.5-turbo" (with dash)
        # Accept either variant to be robust
        assert ("reverting to gpt-3.5.turbo" in out) or ("reverting to gpt-3.5-turbo" in out)
        # Also check that the internal kwargs model is set correctly
        assert instance.kwargs.get("model") == "gpt-3.5-turbo"


def test_ai_start_and_next_methods_work_normally():
    # Patch openai.ChatCompletion.create to simulate streaming response
    def dummy_create(*args, **kwargs):
        class DummyStream:
            def __iter__(self_inner):
                # Simulate streaming chunks of response
                yield {"choices": [{"delta": {"content": "Hello"}}]}
                yield {"choices": [{"delta": {"content": " World"}}]}
                yield {"choices": [{"delta": {}}]}  # End of stream

        return DummyStream()

    # Patch openai.Model.retrieve to succeed (no exception)
    with patch.object(ai.openai, "Model") as mock_model, \
         patch.object(ai.openai.ChatCompletion, "create", side_effect=dummy_create), \
         patch.object(ai.openai, "error", create=True) as mock_error:
        mock_error.InvalidRequestError = Exception  # dummy, won't be raised
        mock_model.retrieve.return_value = MagicMock()

        instance = ai.AI()
        system_prompt = "You are a helpful assistant."
        user_prompt = "Say hello."

        messages = instance.start(system_prompt, user_prompt)
        # The start method returns a list with system and user messages
        assert isinstance(messages, list)
        assert any(m.get("role") == "system" for m in messages)
        assert any(m.get("role") == "user" for m in messages)

        # Now test next() appends the assistant message correctly
        new_messages = instance.next(messages)
        # The new_messages should have one more message than messages
        assert len(new_messages) == len(messages) + 1
        # The last message role should be assistant
        assert new_messages[-1]["role"] == "assistant"
        # The content should be "Hello World"
        assert new_messages[-1]["content"] == "Hello World"


def test_ai_next_appends_assistant_message_correctly():
    # Patch openai.ChatCompletion.create to simulate streaming response with different content
    def dummy_create(*args, **kwargs):
        class DummyStream:
            def __iter__(self_inner):
                yield {"choices": [{"delta": {"content": "Test"}}]}
                yield {"choices": [{"delta": {"content": " message"}}]}
                yield {"choices": [{"delta": {}}]}

        return DummyStream()

    # Patch openai.Model.retrieve to succeed (no exception)
    with patch.object(ai.openai, "Model") as mock_model, \
         patch.object(ai.openai.ChatCompletion, "create", side_effect=dummy_create), \
         patch.object(ai.openai, "error", create=True) as mock_error:
        mock_error.InvalidRequestError = Exception  # dummy, won't be raised
        mock_model.retrieve.return_value = MagicMock()

        instance = ai.AI()
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "user", "content": "User message"},
        ]

        new_messages = instance.next(messages)
        assert len(new_messages) == len(messages) + 1
        assert new_messages[-1]["role"] == "assistant"
        assert new_messages[-1]["content"] == "Test message"
