import copy

import pytest

from strands.models import BedrockModel, CacheConfig


def test_supports_caching_true_for_claude():
    """Test that supports_caching returns True for Claude models."""
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")
    assert model._supports_caching is True

    model2 = BedrockModel(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    assert model2._supports_caching is True


def test_supports_caching_false_for_non_claude():
    """Test that supports_caching returns False for non-Claude models."""
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")
    assert model._supports_caching is False


def test_inject_cache_point_adds_to_last_assistant():
    """Test that _inject_cache_point adds cache point to last assistant message."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", cache_config=CacheConfig(strategy="auto")
    )

    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
    ]

    model._inject_cache_point(cleaned_messages)

    assert len(cleaned_messages[1]["content"]) == 2
    assert "cachePoint" in cleaned_messages[1]["content"][-1]
    assert cleaned_messages[1]["content"][-1]["cachePoint"]["type"] == "default"


def test_inject_cache_point_no_assistant_message():
    """Test that _inject_cache_point does nothing when no assistant message exists."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", cache_config=CacheConfig(strategy="auto")
    )

    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
    ]

    model._inject_cache_point(cleaned_messages)

    assert len(cleaned_messages) == 1
    assert len(cleaned_messages[0]["content"]) == 1


def test_inject_cache_point_skipped_for_non_claude():
    """Test that cache point injection is skipped for non-Claude models."""
    model = BedrockModel(model_id="amazon.nova-pro-v1:0", cache_config=CacheConfig(strategy="auto"))

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = model._format_bedrock_messages(messages)

    # The last assistant message content should not have cachePoint injected
    assistant_message = next(msg for msg in formatted if msg["role"] == "assistant")
    # There should be no cachePoint block in the assistant message content
    assert all("cachePoint" not in block for block in assistant_message["content"])


def test_format_bedrock_messages_does_not_mutate_original():
    """Test that _format_bedrock_messages does not mutate original messages."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", cache_config=CacheConfig(strategy="auto")
    )

    original_messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Hi there!"}]},
        {"role": "user", "content": [{"text": "How are you?"}]},
    ]

    messages_before = copy.deepcopy(original_messages)
    formatted = model._format_bedrock_messages(original_messages)

    # Original messages should be unchanged
    assert original_messages == messages_before

    # Original assistant message content should not have cachePoint
    assert all("cachePoint" not in block for block in original_messages[1]["content"])

    # Formatted assistant message content should have cachePoint appended
    assert "cachePoint" in formatted[1]["content"][-1]


def test_inject_cache_point_strips_existing_cache_points():
    """Test that _inject_cache_point strips existing cache points and adds new one at correct position."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", cache_config=CacheConfig(strategy="auto")
    )

    # Messages with existing cache points in various positions
    cleaned_messages = [
        {"role": "user", "content": [{"text": "Hello"}, {"cachePoint": {"type": "default"}}]},
        {"role": "assistant", "content": [{"text": "First response"}, {"cachePoint": {"type": "default"}}]},
        {"role": "user", "content": [{"text": "Follow up"}]},
        {"role": "assistant", "content": [{"text": "Second response"}]},
    ]

    model._inject_cache_point(cleaned_messages)

    # All old cache points should be stripped
    assert len(cleaned_messages[0]["content"]) == 1  # user: only text
    assert len(cleaned_messages[1]["content"]) == 1  # first assistant: only text

    # New cache point should be at end of last assistant message
    assert len(cleaned_messages[3]["content"]) == 2
    assert "cachePoint" in cleaned_messages[3]["content"][-1]
    assert cleaned_messages[3]["content"][-1]["cachePoint"]["type"] == "default"
