import pytest

from crewai.cli.constants import PROVIDERS, ENV_VARS, MODELS


def test_huggingface_in_providers():
    """Test that 'huggingface' is included in the PROVIDERS list."""
    assert "huggingface" in PROVIDERS, "'huggingface' should be in PROVIDERS"


def test_huggingface_env_vars():
    """Test that Huggingface environment variables are properly configured."""
    assert "huggingface" in ENV_VARS, "'huggingface' should be a key in ENV_VARS"
    hf_vars = ENV_VARS["huggingface"]
    assert any(d.get("key_name") == "HF_TOKEN" for d in hf_vars), "HF_TOKEN should be in huggingface ENV_VARS"


def test_huggingface_models():
    """Test that Huggingface models are properly configured."""
    assert "huggingface" in MODELS, "'huggingface' should be a key in MODELS"
    hf_models = MODELS["huggingface"]
    assert isinstance(hf_models, list) and len(hf_models) > 0, "MODELS['huggingface'] should be a non-empty list"
