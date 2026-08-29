import pytest
from strands import Agent, tool
from strands.models import BedrockModel
from botocore.exceptions import NoCredentialsError


@tool
def list_tables_empty_content() -> dict:
    """Tool returning empty content list to simulate empty toolResult content."""
    return {
        "status": "success",
        "content": [],
    }


@tool
def list_tables_nonempty_content() -> dict:
    """Tool returning non-empty content list to simulate normal toolResult content."""
    return {
        "status": "success",
        "content": [{"text": "table1"}, {"text": "table2"}],
    }


def test_format_request_message_content_normalizes_empty_tool_result_content(model_id="m1"):
    """
    Test that BedrockModel._format_request normalizes empty toolResult content to [{'text': ''}].
    This test uses the BedrockModel directly without calling Agent.
    """
    model = BedrockModel(model_id=model_id)

    messages = [
        {"role": "user", "content": [{"text": "List tables"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_001", "name": "run_query", "input": {"sql": "SELECT 1"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_001", "content": []}},
            ],
        },
    ]

    formatted_request = model._format_request(messages)

    tool_result = formatted_request["messages"][2]["content"][0]["toolResult"]
    assert tool_result["content"] == [{"text": ""}], "Empty toolResult content should be normalized to [{'text': ''}]"


def test_format_request_message_content_preserves_nonempty_tool_result_content(model_id="m1"):
    """
    Test that BedrockModel._format_request does not modify non-empty toolResult content.
    """
    model = BedrockModel(model_id=model_id)

    messages = [
        {"role": "user", "content": [{"text": "List tables"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_001", "name": "run_query", "input": {"sql": "SELECT 1"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_001", "content": [{"text": "some result"}]}},
            ],
        },
    ]

    formatted_request = model._format_request(messages)

    tool_result = formatted_request["messages"][2]["content"][0]["toolResult"]
    assert tool_result["content"] == [{"text": "some result"}]


def test_format_request_message_content_does_not_mutate_original(model_id="m1"):
    """
    Test that normalizing empty toolResult content does not mutate the original messages.
    """
    model = BedrockModel(model_id=model_id)

    messages = [
        {"role": "user", "content": [{"text": "List tables"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "tool_001", "name": "run_query", "input": {"sql": "SELECT 1"}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "tool_001", "content": []}},
            ],
        },
    ]

    original_content = messages[2]["content"][0]["toolResult"]["content"]
    model._format_request(messages)

    assert original_content == [], "Original empty content list should not be mutated"
