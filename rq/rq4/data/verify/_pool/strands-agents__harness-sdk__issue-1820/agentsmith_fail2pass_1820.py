import copy
import pytest

from strands.models import BedrockModel, CacheConfig


@pytest.fixture
def claude_model():
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        cache_config=CacheConfig(strategy="auto"),
    )


@pytest.fixture
def non_claude_model():
    return BedrockModel(
        model_id="amazon.nova-pro-v1:0",
        cache_config=CacheConfig(strategy="auto"),
    )


def test_inject_cache_point_adds_to_last_user(claude_model):
    """
    Test that _inject_cache_point adds a cache point to the last user message content,
    not the last assistant message.
    """
    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
    ]

    claude_model._inject_cache_point(cleaned_messages)

    # The cache point should be added to the last user message (index 2)
    assert len(cleaned_messages[2]["content"]) == 2
    assert "cachePoint" in cleaned_messages[2]["content"][-1]
    assert cleaned_messages[2]["content"][-1]["cachePoint"]["type"] == "default"

    # The assistant message content should remain unchanged
    assert len(cleaned_messages[1]["content"]) == 1


def test_inject_cache_point_single_user_message(claude_model):
    """
    Test that _inject_cache_point adds a cache point to a single user message.
    """
    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
    ]

    claude_model._inject_cache_point(cleaned_messages)

    assert len(cleaned_messages) == 1
    assert len(cleaned_messages[0]["content"]) == 2
    assert "cachePoint" in cleaned_messages[0]["content"][-1]
    assert cleaned_messages[0]["content"][-1]["cachePoint"]["type"] == "default"


def test_inject_cache_point_empty_messages(claude_model):
    """
    Test that _inject_cache_point handles empty messages list gracefully.
    """
    cleaned_messages = []

    claude_model._inject_cache_point(cleaned_messages)

    assert cleaned_messages == []


def test_inject_cache_point_with_tool_result_last_user(claude_model):
    """
    Test that cache point is added to last user message even when it contains toolResult.
    """
    cleaned_messages = [
        {"role": "user", "content": [{"text": "Use the tool"}]},
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": "test_tool", "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "content": [{"text": "Result"}]}}]},
    ]

    claude_model._inject_cache_point(cleaned_messages)

    # Cache point should be added to last user message (index 2)
    assert len(cleaned_messages[2]["content"]) == 2
    assert "cachePoint" in cleaned_messages[2]["content"][-1]
    assert cleaned_messages[2]["content"][-1]["cachePoint"]["type"] == "default"

    # Other user message content unchanged
    assert len(cleaned_messages[0]["content"]) == 1


def test_inject_cache_point_skipped_for_non_claude(non_claude_model):
    """
    Test that cache point injection is skipped for non-Claude models.
    """
    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = non_claude_model._format_bedrock_messages(messages)

    # Neither user nor assistant message should have cachePoint added
    assert len(formatted[0]["content"]) == 1
    assert "cachePoint" not in formatted[0]["content"][0]
    assert len(formatted[1]["content"]) == 1
    assert "cachePoint" not in formatted[1]["content"][0]


def test_format_bedrock_messages_does_not_mutate_original(claude_model):
    """
    Test that _format_bedrock_messages does not mutate the original messages list.
    """
    original_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
    ]

    messages_before = copy.deepcopy(original_messages)
    formatted = claude_model._format_bedrock_messages(original_messages)

    # Original messages must remain unchanged
    assert original_messages == messages_before

    # Cache point should NOT be in original messages
    assert "cachePoint" not in original_messages[2]["content"][-1]

    # Cache point should be added in formatted messages to last user message
    assert "cachePoint" in formatted[2]["content"][-1]


def test_inject_cache_point_strips_existing_cache_points(claude_model):
    """
    Test that _inject_cache_point strips existing cache points and adds a new one at the correct position.
    """
    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}, {"cachePoint": {"type": "default"}}]},
        {"role": "assistant", "content": [{"text": "First response"}, {"cachePoint": {"type": "default"}}]},
        {"role": "user", "content": [{"text": "Follow up"}]},
        {"role": "assistant", "content": [{"text": "Second response"}]},
    ]

    claude_model._inject_cache_point(cleaned_messages)

    # All old cache points should be stripped from user messages
    assert len(cleaned_messages[0]["content"]) == 1  # first user: only text
    assert len(cleaned_messages[1]["content"]) == 1  # first assistant: only text
    assert len(cleaned_messages[3]["content"]) == 1  # last assistant: only text

    # New cache point should be at end of last user message (index 2)
    assert len(cleaned_messages[2]["content"]) == 2
    assert "cachePoint" in cleaned_messages[2]["content"][-1]


def test_inject_cache_point_anthropic_strategy_skips_model_check():
    """
    Test that anthropic strategy injects cache point without model support check.
    """
    model = BedrockModel(
        model_id="arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/a1b2c3d4e5f6",
        cache_config=CacheConfig(strategy="anthropic"),
    )

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = model._format_bedrock_messages(messages)

    # Cache point should be added to last user message (index 0)
    assert len(formatted[0]["content"]) == 2
    assert "cachePoint" in formatted[0]["content"][-1]
    assert formatted[0]["content"][-1]["cachePoint"]["type"] == "default"

    # Assistant message content unchanged
    assert len(formatted[1]["content"]) == 1


def test_inject_cache_point_auto_strategy_resolves_to_anthropic_for_claude():
    """
    Test that auto strategy resolves to anthropic strategy for Claude models.
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        cache_config=CacheConfig(strategy="auto"),
    )

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = model._format_bedrock_messages(messages)

    # Cache point should be added to last user message (index 0)
    assert len(formatted[0]["content"]) == 2
    assert "cachePoint" in formatted[0]["content"][-1]

    # Assistant message content unchanged
    assert len(formatted[1]["content"]) == 1
