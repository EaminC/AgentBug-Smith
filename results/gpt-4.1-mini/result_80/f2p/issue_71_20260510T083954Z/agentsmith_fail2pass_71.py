import pytest
from unittest.mock import patch, MagicMock

from src.agentscope.models.openai_model import OpenAIChatWrapper
from src.agentscope.message import Msg


@pytest.fixture
def openai_model():
    # The OpenAIChatWrapper requires a config_name argument as per the constructor
    # Provide a dummy config_name and patch the internal client call to avoid real API requests
    model = OpenAIChatWrapper(config_name="gpt-3.5-turbo")
    # Patch the internal call to openai chat completions to avoid network calls
    # The real __call__ method uses self.client.chat.completions.create internally
    # We patch that to return a dummy response with a .choices[0].message.content attribute
    dummy_response = MagicMock()
    dummy_response.choices = [MagicMock()]
    dummy_response.choices[0].message.content = "dummy response"
    dummy_response.choices[0].message.role = "assistant"

    patcher = patch.object(model.client.chat.completions, "create", return_value=dummy_response)
    patcher.start()
    yield model
    patcher.stop()


def test_openai_model_accepts_list_of_dicts_with_role_and_content(openai_model):
    # messages as list of dicts with role and content keys
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result = openai_model(messages)
    assert hasattr(result, "text") or hasattr(result, "content")


def test_openai_model_accepts_list_of_Msg_objects(openai_model):
    # messages as list of Msg objects
    messages = [
        Msg(name="user", role="user", content="Hello"),
        Msg(name="assistant", role="assistant", content="Hi there!"),
    ]
    result = openai_model(messages)
    assert hasattr(result, "text") or hasattr(result, "content")


def test_openai_model_accepts_list_of_messages(openai_model):
    # messages as list of mixed dict and Msg objects (should still work if Msg supports dict interface)
    messages = [
        {"role": "user", "content": "Hello"},
        Msg(name="assistant", role="assistant", content="Hi there!"),
    ]
    result = openai_model(messages)
    assert hasattr(result, "text") or hasattr(result, "content")


def test_openai_model_rejects_single_dict_not_in_list(openai_model):
    # Single dict (not in list) should raise ValueError about expected list type
    single_message = {"role": "user", "content": "Hello"}
    with pytest.raises(ValueError) as excinfo:
        openai_model(single_message)
    assert "expected type `list`" in str(excinfo.value)


def test_openai_model_rejects_list_missing_role_or_content(openai_model):
    # List with one dict missing 'role' or 'content' keys should raise ValueError
    bad_messages = [
        {"role": "user", "content": "Hello"},
        {"content": "Missing role"},
    ]
    with pytest.raises(ValueError) as excinfo:
        openai_model(bad_messages)
    assert "must contain a 'role' and 'content' key" in str(excinfo.value)


def test_openai_model_accepts_single_Msg_object_wrapped_in_list(openai_model):
    # Single Msg object wrapped in a list should be accepted
    single_msg_list = [Msg(name="user", role="user", content="Hello")]
    result = openai_model(single_msg_list)
    assert hasattr(result, "text") or hasattr(result, "content")
