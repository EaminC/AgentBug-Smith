import pytest

from strands.models.openai import OpenAIModel


@pytest.mark.parametrize(
    ("model_id", "expected_path"),
    [
        # Regression for #3654: Mantle rejects the wrong base path with HTTP 400
        # validation_error. The affected ids use /openai/v1; controls below pin /v1.
        ("xai.grok-4.3", "/openai/v1"),
        ("google.gemma-4-31b", "/openai/v1"),
        ("google.gemma-4-26b-a4b", "/openai/v1"),
        ("google.gemma-4-e2b", "/openai/v1"),
        ("openai.gpt-5.6-terra", "/openai/v1"),
        # Gemma 3 is served from /v1 while Gemma 4 is not, so `google.` cannot be a prefix.
        ("google.gemma-3-27b-it", "/v1"),
        ("google.gemma-3-4b-it", "/v1"),
        ("openai.gpt-oss-120b", "/v1"),
        ("openai.gpt-oss-safeguard-20b", "/v1"),
        ("qwen.qwen3-32b", "/v1"),
        ("deepseek.v3.2", "/v1"),
        ("mistral.ministral-3-8b-instruct", "/v1"),
        ("zai.glm-5", "/v1"),
        ("moonshotai.kimi-k2.5", "/v1"),
        ("minimax.minimax-m2", "/v1"),
        ("nvidia.nemotron-nano-9b-v2", "/v1"),
        ("writer.palmyra-vision-7b", "/v1"),
    ],
)
def test_bedrock_mantle_config_base_path_per_model(model_id, expected_path):
    """Each Mantle model resolves to the base path it is actually served from."""
    model = OpenAIModel(model_id=model_id, bedrock_mantle_config={"region": "us-east-1"})

    resolved = model._resolve_client_args()
    assert resolved["base_url"] == f"https://bedrock-mantle.us-east-1.api.aws{expected_path}"


@pytest.mark.parametrize(
    ("model_id", "expected_path"),
    [
        # Point releases within a verified line, beyond the verified catalog.
        ("xai.grok-4.9", "/openai/v1"),
        ("openai.gpt-5.9-unreleased", "/openai/v1"),
        # New lines the prefixes deliberately do not cover.
        ("xai.grok-5", "/v1"),
        ("xai.grok-5-preview", "/v1"),
    ],
)
def test_bedrock_mantle_config_unverified_ids(model_id, expected_path):
    """Ids beyond the verified catalog: a known line routes by prefix, a new line falls to /v1."""
    model = OpenAIModel(model_id=model_id, bedrock_mantle_config={"region": "us-east-1"})

    resolved = model._resolve_client_args()
    assert resolved["base_url"] == f"https://bedrock-mantle.us-east-1.api.aws{expected_path}"
