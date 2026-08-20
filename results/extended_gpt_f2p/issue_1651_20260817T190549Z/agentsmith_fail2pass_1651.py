import pytest
from strands.models import BedrockModel


@pytest.mark.asyncio
async def test_format_request_with_guardrail_latest_message_after_tool_use():
    """Test that guardContent wraps the last user text message even when a toolResult follows it."""
    model = BedrockModel(
        model_id="test-model",
        guardrail_id="test-guardrail",
        guardrail_version="DRAFT",
        guardrail_latest_message=True,
    )

    messages = [
        {"role": "user", "content": [{"text": "First message"}]},
        {"role": "assistant", "content": [{"text": "First response"}]},
        {"role": "user", "content": [{"text": "what is the standard deduction?"}]},
        {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "tool-1",
                        "name": "knowledge_base",
                        "input": {"query": "standard deduction"},
                    }
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "tool-1",
                        "content": [{"text": "The standard deduction for 2024 is $14,600."}],
                        "status": "success",
                    }
                }
            ],
        },
    ]

    request = model._format_request(messages)
    formatted_messages = request["messages"]

    assert len(formatted_messages) == 5

    # Earlier user message with text should be wrapped
    assert "guardContent" in formatted_messages[2]["content"][0]
    assert formatted_messages[2]["content"][0]["guardContent"]["text"]["text"] == "what is the standard deduction?"

    # toolResult-only user message should NOT be wrapped
    assert "toolResult" in formatted_messages[4]["content"][0]
    assert "guardContent" not in formatted_messages[4]["content"][0]

    # The first user message should NOT be wrapped
    assert "text" in formatted_messages[0]["content"][0]
    assert "guardContent" not in formatted_messages[0]["content"][0]


@pytest.mark.asyncio
async def test_format_request_with_guardrail_latest_message_wraps_final_user_text():
    """Test that guardContent wraps the last user message when it contains text content."""
    model = BedrockModel(
        model_id="test-model",
        guardrail_id="test-guardrail",
        guardrail_version="DRAFT",
        guardrail_latest_message=True,
    )

    messages = [
        {"role": "user", "content": [{"text": "First message"}]},
        {"role": "assistant", "content": [{"text": "First response"}]},
        {"role": "user", "content": [{"text": "Tell me about taxes"}]},
    ]

    request = model._format_request(messages)
    formatted_messages = request["messages"]

    assert "guardContent" in formatted_messages[2]["content"][0]
    assert formatted_messages[2]["content"][0]["guardContent"]["text"]["text"] == "Tell me about taxes"


@pytest.mark.asyncio
async def test_format_request_with_guardrail_multiple_sequential_tool_calls():
    """Test guardContent with multiple tool calls in sequence (no new user input between)."""
    model = BedrockModel(
        model_id="test-model",
        guardrail_id="test-guardrail",
        guardrail_version="DRAFT",
        guardrail_latest_message=True,
    )

    messages = [
        {"role": "user", "content": [{"text": "First question"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "tool1", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "Result 1"}], "status": "success"}}],
        },
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t2", "name": "tool2", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t2", "content": [{"text": "Result 2"}], "status": "success"}}],
        },
    ]

    request = model._format_request(messages)
    formatted_messages = request["messages"]

    # Should wrap the first user text message, not the toolResults
    assert "guardContent" in formatted_messages[0]["content"][0]
    assert formatted_messages[0]["content"][0]["guardContent"]["text"]["text"] == "First question"

    # toolResults should not be wrapped
    assert "toolResult" in formatted_messages[2]["content"][0]
    assert "guardContent" not in formatted_messages[2]["content"][0]
    assert "toolResult" in formatted_messages[4]["content"][0]
    assert "guardContent" not in formatted_messages[4]["content"][0]


@pytest.mark.asyncio
async def test_format_request_with_guardrail_image_before_tool_result():
    """Test guardContent wraps image content even when toolResult follows."""
    model = BedrockModel(
        model_id="test-model",
        guardrail_id="test-guardrail",
        guardrail_version="DRAFT",
        guardrail_latest_message=True,
    )

    messages = [
        {"role": "user", "content": [{"image": {"format": "png", "source": {"bytes": b"fake"}}}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "vision", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "I see a cat"}], "status": "success"}}],
        },
    ]

    request = model._format_request(messages)
    formatted_messages = request["messages"]

    # Image should be wrapped even though toolResult comes after
    assert "guardContent" in formatted_messages[0]["content"][0]
    assert "image" in formatted_messages[0]["content"][0]["guardContent"]


@pytest.mark.asyncio
async def test_format_request_with_guardrail_multiple_tool_results_same_message():
    """Test guardContent with multiple parallel tool calls (multiple toolResults in one message)."""
    model = BedrockModel(
        model_id="test-model",
        guardrail_id="test-guardrail",
        guardrail_version="DRAFT",
        guardrail_latest_message=True,
    )

    messages = [
        {"role": "user", "content": [{"text": "Question requiring multiple tools"}]},
        {
            "role": "assistant",
            "content": [
                {"toolUse": {"toolUseId": "t1", "name": "tool1", "input": {}}},
                {"toolUse": {"toolUseId": "t2", "name": "tool2", "input": {}}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"toolResult": {"toolUseId": "t1", "content": [{"text": "Result 1"}], "status": "success"}},
                {"toolResult": {"toolUseId": "t2", "content": [{"text": "Result 2"}], "status": "success"}},
            ],
        },
    ]

    request = model._format_request(messages)
    formatted_messages = request["messages"]

    # Should wrap the question
    assert "guardContent" in formatted_messages[0]["content"][0]
    assert formatted_messages[0]["content"][0]["guardContent"]["text"]["text"] == "Question requiring multiple tools"


def test_find_last_user_text_message_index_no_user_messages():
    """Test _find_last_user_text_message_index returns None when no user text messages exist."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {"role": "assistant", "content": [{"text": "hello"}]},
    ]

    assert model._find_last_user_text_message_index(messages) is None


def test_find_last_user_text_message_index_only_tool_results():
    """Test _find_last_user_text_message_index returns None when user messages only have toolResult."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "result"}]}}],
        },
    ]

    assert model._find_last_user_text_message_index(messages) is None


def test_find_last_user_text_message_index_returns_last_text_message():
    """Test _find_last_user_text_message_index returns the index of the last user message with text."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {"role": "user", "content": [{"text": "First question"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
        {"role": "user", "content": [{"text": "Second question"}]},
    ]

    assert model._find_last_user_text_message_index(messages) == 2


def test_find_last_user_text_message_index_skips_tool_result_messages():
    """Test _find_last_user_text_message_index skips toolResult-only user messages."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {"role": "user", "content": [{"text": "Question"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "tool", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "Result"}]}}],
        },
    ]

    assert model._find_last_user_text_message_index(messages) == 0


def test_find_last_user_text_message_index_finds_image_message():
    """Test _find_last_user_text_message_index finds user messages with image content."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {"role": "user", "content": [{"image": {"format": "png", "source": {"bytes": b"fake"}}}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "vision", "input": {}}}]},
        {
            "role": "user",
            "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "Result"}]}}],
        },
    ]

    assert model._find_last_user_text_message_index(messages) == 0


def test_find_last_user_text_message_index_empty_messages():
    """Test _find_last_user_text_message_index returns None for empty message list."""
    model = BedrockModel(model_id="test-model")

    assert model._find_last_user_text_message_index([]) is None


def test_guardrail_latest_message_disabled_does_not_wrap():
    """Test that guardContent wrapping is skipped when guardrail_latest_message is not set."""
    model = BedrockModel(model_id="test-model")

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
    ]

    request = model._format_request(messages)
    formatted = request["messages"][0]["content"][0]

    assert "text" in formatted
    assert "guardContent" not in formatted
