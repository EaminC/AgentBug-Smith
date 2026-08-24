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


@pytest.mark.parametrize("model_id", [
    "nvidia.nemotron-super-3-120b",
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
])
def test_agent_tool_result_content_normalization(model_id):
    """
    Test that agents using BedrockModel with tools returning empty or non-empty toolResult content
    behave correctly.

    - For Nemotron model, empty toolResult content should be normalized to [{'text': ''}] to avoid ValidationException.
    - For Claude model, empty toolResult content is accepted as is.
    - Both models should succeed with non-empty toolResult content.
    """

    # Select the tool based on test case
    # For empty content test, use list_tables_empty_content
    # For non-empty content test, use list_tables_nonempty_content
    # We will test both scenarios below.

    # Test empty content tool
    agent_empty = Agent(
        model=BedrockModel(model_id=model_id, streaming=False),
        tools=[list_tables_empty_content],
    )

    # Test non-empty content tool
    agent_nonempty = Agent(
        model=BedrockModel(model_id=model_id, streaming=False),
        tools=[list_tables_nonempty_content],
    )

    # Run the agent with empty content tool and check behavior
    # Nemotron model should succeed after patch (fail before patch)
    # Claude model should always succeed
    try:
        result_empty = agent_empty("What tables are in the database?")
    except NoCredentialsError:
        pytest.skip("AWS credentials not configured; skipping live Bedrock API test")
    except Exception as e:
        # For Nemotron model before fix, expect ValidationException or similar
        if model_id == "nvidia.nemotron-super-3-120b":
            # This test is fail2pass, so on buggy code it should fail here
            # We re-raise to mark test failure on buggy code
            raise
        else:
            # For Claude or other models, no exception expected
            raise
    else:
        # On fixed code, no exception expected
        assert result_empty is not None
        # The result should contain some text output or at least be a valid response string
        assert isinstance(result_empty, str)
        assert len(result_empty) > 0

    # Run the agent with non-empty content tool and check behavior
    try:
        result_nonempty = agent_nonempty("What tables are in the database?")
    except NoCredentialsError:
        pytest.skip("AWS credentials not configured; skipping live Bedrock API test")
    else:
        assert result_nonempty is not None
        assert isinstance(result_nonempty, str)
        assert "table1" in result_nonempty or "table2" in result_nonempty


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
