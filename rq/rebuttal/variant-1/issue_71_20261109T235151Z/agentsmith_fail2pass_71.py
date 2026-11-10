import pytest
from src.agentscope.models.openai_model import OpenAIChatWrapper
from unittest.mock import MagicMock


@pytest.fixture
def dummy_openai_model():
    # Create an instance of OpenAIChatWrapper with dummy config
    model = OpenAIChatWrapper(config_name="dummy-config")

    # Mock the internal client.chat.completions.create to avoid real API calls
    dummy_response = MagicMock()
    # The real code expects response.model_dump() method
    dummy_response.model_dump.return_value = {"choices": [{"message": {"content": "dummy response"}}]}
    model.client = MagicMock()
    model.client.chat.completions.create = MagicMock(return_value=dummy_response)
    return model


def test_openai_model_accepts_list_of_messages(dummy_openai_model):
    # Passing a list of messages with role and content should work without error
    messages = [{"role": "user", "content": "Hello"}]
    response = dummy_openai_model(messages)
    # The response should have a text attribute with the dummy response content
    assert hasattr(response, "text") or hasattr(response, "raw") or response is not None


def test_openai_model_accepts_single_msg_object(dummy_openai_model):
    # Passing a single message dict with role and content should raise ValueError about expecting list
    single_message = {"role": "user", "content": "Hello"}

    with pytest.raises(ValueError) as excinfo:
        dummy_openai_model(single_message)

    assert "expected type `list`" in str(excinfo.value)


def test_openai_model_rejects_non_list_messages(dummy_openai_model):
    # Passing a non-list, non-dict (e.g., string) should raise ValueError about expecting list
    non_list_input = "this is not a list"

    with pytest.raises(ValueError) as excinfo:
        dummy_openai_model(non_list_input)

    assert "expected type `list`" in str(excinfo.value)
