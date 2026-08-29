import pytest
import strands.models.openai_responses as openai_responses


def test_assistant_history_serialization_shape():
    """
    Regression test for issue #3388:
    Assistant messages in multi-turn conversations must serialize the content as a string,
    not as a list of output_text dicts, to conform to the valid Responses API input shape.

    Before the fix, the assistant content is a list of dicts with type=output_text,
    which is rejected by strict backends like Bedrock Mantle.

    After the fix, the assistant content is a single string joining all text blocks with newlines.
    """
    messages = [
        {
            "role": "user",
            "content": [{"text": "What is 2+2?"}],
        },
        {
            "role": "assistant",
            "content": [{"text": "4"}],
        },
        {
            "role": "user",
            "content": [{"text": "What about 3+3?"}],
        },
    ]

    formatted = openai_responses.OpenAIResponsesModel._format_request_messages(messages)

    # The assistant message content must be a string, not a list of dicts
    assistant_msg = formatted[1]
    assert assistant_msg["role"] == "assistant"
    assert isinstance(assistant_msg["content"], str)
    assert assistant_msg["content"] == "4"

    # User messages remain lists of dicts with type input_text
    user_msg_0 = formatted[0]
    assert user_msg_0["role"] == "user"
    assert isinstance(user_msg_0["content"], list)
    assert user_msg_0["content"][0]["type"] == "input_text"
    assert user_msg_0["content"][0]["text"] == "What is 2+2?"

    user_msg_2 = formatted[2]
    assert user_msg_2["role"] == "user"
    assert isinstance(user_msg_2["content"], list)
    assert user_msg_2["content"][0]["type"] == "input_text"
    assert user_msg_2["content"][0]["text"] == "What about 3+3?"


def test_assistant_multiple_text_blocks_joined():
    """
    Assistant messages with multiple text blocks must join them with newlines into a single string.
    """
    messages = [
        {
            "role": "assistant",
            "content": [{"text": "First."}, {"text": "Second."}],
        }
    ]

    formatted = openai_responses.OpenAIResponsesModel._format_request_messages(messages)

    assert len(formatted) == 1
    assistant_msg = formatted[0]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "First.\nSecond."


def test_assistant_non_text_content_dropped_with_warning(caplog):
    """
    Assistant messages containing non-text content (e.g. images) drop those parts with a warning,
    and only the text parts are serialized as a string.
    """
    messages = [
        {
            "role": "assistant",
            "content": [
                {"text": "Here is the image."},
                {"image": {"format": "png", "source": {"bytes": b"fake-image-data"}}},
            ],
        }
    ]

    with caplog.at_level("WARNING", logger="strands.models.openai_responses"):
        formatted = openai_responses.OpenAIResponsesModel._format_request_messages(messages)

    assert len(formatted) == 1
    assistant_msg = formatted[0]
    assert assistant_msg["role"] == "assistant"
    assert assistant_msg["content"] == "Here is the image."
    assert "content_type=<input_image>" in caplog.text


def test_assistant_only_non_text_content_dropped_entirely(caplog):
    """
    An assistant message whose content is entirely non-text is dropped entirely,
    and a warning is logged.
    """
    messages = [
        {
            "role": "assistant",
            "content": [
                {"image": {"format": "png", "source": {"bytes": b"fake-image-data"}}},
            ],
        }
    ]

    with caplog.at_level("WARNING", logger="strands.models.openai_responses"):
        formatted = openai_responses.OpenAIResponsesModel._format_request_messages(messages)

    # No assistant messages remain after dropping non-text only content
    assert all(msg["role"] != "assistant" for msg in formatted)
    assert "content_type=<input_image>" in caplog.text


@pytest.mark.parametrize("role", ["user", "assistant"])
def test_format_request_message_content_text_type(role):
    """
    _format_request_message_content returns correct type field depending on role.
    For assistant role, type is 'output_text'.
    For user role, type is 'input_text'.
    """
    content = {"text": "sample text"}
    formatted = openai_responses.OpenAIResponsesModel._format_request_message_content(content, role=role)
    if role == "assistant":
        assert formatted == {"type": "output_text", "text": "sample text"}
    else:
        assert formatted == {"type": "input_text", "text": "sample text"}


def test_format_request_messages_assistant_history_items_are_valid_input_items():
    """
    The formatted assistant history messages conform to the OpenAI EasyInputMessage shape:
    keys are a subset of EasyInputMessageParam, and content is a string.
    """
    import openai

    messages = [
        {"role": "user", "content": [{"text": "What is 2+2?"}]},
        {"role": "assistant", "content": [{"text": "4"}]},
        {"role": "user", "content": [{"text": "What about 3+3?"}]},
    ]

    formatted = openai_responses.OpenAIResponsesModel._format_request_messages(messages)

    assistant_item = formatted[1]
    easy_message_fields = set(openai.types.responses.EasyInputMessageParam.__annotations__)
    # The assistant message keys must be subset of EasyInputMessageParam keys
    assert set(assistant_item.keys()) <= easy_message_fields
    # The content must be a string
    assert isinstance(assistant_item["content"], str)
    assert assistant_item["content"] == "4"
