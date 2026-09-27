import pytest

from strands.models.bedrock import BedrockModel


def test_format_request_message_content_empty_block_raises_type_error():
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    messages = [{"role": "user", "content": [{}]}]

    with pytest.raises(TypeError, match="content_type=<None> \\| unsupported type"):
        model._format_bedrock_messages(messages)
