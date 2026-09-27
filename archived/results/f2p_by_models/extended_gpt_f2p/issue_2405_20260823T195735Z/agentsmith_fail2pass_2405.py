import os
import pytest

from strands.models.openai_responses import OpenAIResponsesModel


def test_tools_list_does_not_grow_across_multiple_format_request_calls():
    """
    This test verifies that calling _format_request multiple times on the same model instance
    with the same tools does not mutate the internal config['params']['tools'] list by duplicating tools.

    Buggy behavior: tools list grows by duplicating tools on each call.
    Fixed behavior: tools list remains constant.
    """
    # Setup initial model with one built-in tool in params
    initial_tools = [{"type": "web_search"}]
    tool_specs = [
        {
            "name": "hello_world",
            "description": "A hello world test tool",
            "inputSchema": {"json": {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]}},
        }
    ]
    messages = [{"role": "user", "content": [{"text": "test"}]}]

    model = OpenAIResponsesModel(model_id="gpt-4o", params={"tools": initial_tools.copy()})

    # Call _format_request multiple times
    request1 = model._format_request(messages, tool_specs)
    request2 = model._format_request(messages, tool_specs)
    request3 = model._format_request(messages, tool_specs)

    # Extract the tools lists from each request
    tools1 = request1.get("tools", [])
    tools2 = request2.get("tools", [])
    tools3 = request3.get("tools", [])

    # The tools list in each request should be identical
    assert tools1 == tools2 == tools3, "Tools list should not grow or change across calls"

    # The model's internal config['params']['tools'] should remain unchanged (no duplication)
    assert model.config["params"]["tools"] == initial_tools, (
        "Internal config['params']['tools'] should not be mutated or duplicated"
    )

    # The tools list should contain exactly the built-in tool plus the function tool once each
    expected_tools = [
        {"type": "web_search"},
        {
            "type": "function",
            "name": "hello_world",
            "description": "A hello world test tool",
            "parameters": {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
        },
    ]
    assert tools1 == expected_tools, "Tools list should contain exactly the built-in and function tools once"


def test_format_request_does_not_mutate_params_tools_across_calls(messages=None, tool_specs=None):
    """
    This test is adapted from the patch's added test to confirm the fix.
    It ensures that the internal params['tools'] list is not mutated across multiple calls.
    """
    if messages is None:
        messages = [{"role": "user", "content": [{"text": "test"}]}]
    if tool_specs is None:
        tool_specs = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "input": {"type": "string"},
                        },
                        "required": ["input"],
                    },
                },
            },
        ]

    model = OpenAIResponsesModel(
        model_id="gpt-4o",
        params={"tools": [{"type": "web_search"}]},
    )

    first = model._format_request(messages, tool_specs)
    second = model._format_request(messages, tool_specs)

    assert second["tools"] == first["tools"], "Tools list should be identical across calls"
    assert model.config["params"]["tools"] == [{"type": "web_search"}], "Internal params['tools'] should not be mutated"


# The following fixtures and imports are copied from strands-py/tests/strands/models/test_openai_responses.py
# to allow this test file to run standalone if needed.

@pytest.fixture
def messages():
    return [{"role": "user", "content": [{"text": "test"}]}]


@pytest.fixture
def tool_specs():
    return [
        {
            "name": "test_tool",
            "description": "A test tool",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                    },
                    "required": ["input"],
                },
            },
        },
    ]


@pytest.mark.parametrize("messages", [None])
@pytest.mark.parametrize("tool_specs", [None])
def test_format_request_does_not_mutate_params_tools_across_calls_param(messages, tool_specs):
    test_format_request_does_not_mutate_params_tools_across_calls(messages, tool_specs)
