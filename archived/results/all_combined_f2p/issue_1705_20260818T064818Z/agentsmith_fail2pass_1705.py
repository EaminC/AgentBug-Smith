import pytest

from strands.models import BedrockModel, CacheConfig


def test_inject_cache_point_anthropic_strategy_skips_model_check():
    """Test that anthropic strategy injects cache point without model support check."""
    model = BedrockModel(
        model_id="arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/a1b2c3d4e5f6",
        cache_config=CacheConfig(strategy="anthropic"),
    )

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = model._format_bedrock_messages(messages)

    assert len(formatted[1]["content"]) == 2
    assert "cachePoint" in formatted[1]["content"][-1]
    assert formatted[1]["content"][-1]["cachePoint"]["type"] == "default"


def test_inject_cache_point_auto_strategy_resolves_to_anthropic_for_claude():
    """Test that auto strategy resolves to anthropic strategy for Claude models."""
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0", cache_config=CacheConfig(strategy="auto")
    )

    messages = [
        {"role": "user", "content": [{"text": "Hello"}]},
        {"role": "assistant", "content": [{"text": "Response"}]},
    ]

    formatted = model._format_bedrock_messages(messages)

    assert len(formatted[1]["content"]) == 2
    assert "cachePoint" in formatted[1]["content"][-1]


def test_cache_strategy_anthropic_for_claude():
    """Test that _cache_strategy returns 'anthropic' for Claude models."""
    model = BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0")
    assert model._cache_strategy == "anthropic"

    model2 = BedrockModel(model_id="anthropic.claude-3-haiku-20240307-v1:0")
    assert model2._cache_strategy == "anthropic"


def test_cache_strategy_none_for_non_claude():
    """Test that _cache_strategy returns None for unsupported models."""
    model = BedrockModel(model_id="amazon.nova-pro-v1:0")
    assert model._cache_strategy is None
