import os
import pytest
from mle import model


def test_openai_model_base_url_forwarding(monkeypatch):
    """
    Test that OpenAIModel correctly uses the OPENAI_BASE_URL environment variable
    for its base_url parameter when initialized via load_model.
    This test verifies that the API base URL forwarding works as intended.
    """

    # Set environment variable for custom base URL
    custom_base_url = "https://custom.openai.api/v1"
    monkeypatch.setenv("OPENAI_BASE_URL", custom_base_url)

    dummy_api_key = "dummy_api_key_123"

    def dummy_get_config(project_dir):
        return {
            "platform": model.MODEL_OPENAI,
            "api_key": dummy_api_key,
        }

    original_get_config = model.get_config
    model.get_config = dummy_get_config

    try:
        m = model.load_model(project_dir="dummy_project_dir")

        # The model instance should be an OpenAIModel or wrapped by ObservableModel
        # The bug is that load_model returns ObservableModel wrapping the real model
        # So unwrap if needed:
        real_model = m
        if hasattr(m, "model"):
            real_model = m.model

        assert real_model.__class__.__name__ == "OpenAIModel"

        # The client attribute should have the base_url set to the custom value
        base_url = getattr(real_model.client, "base_url", None)
        if base_url is not None:
            base_url_str = str(base_url).rstrip("/")
        else:
            base_url_str = None

        assert base_url_str == custom_base_url

    finally:
        model.get_config = original_get_config


def test_claude_model_load(monkeypatch):
    """
    Test that load_model returns a ClaudeModel instance with correct api_key
    when platform is set to 'claude' in config.
    """

    dummy_api_key = "dummy_claude_key"

    def dummy_get_config(project_dir):
        return {
            "platform": model.MODEL_CLAUDE,
            "api_key": dummy_api_key,
        }

    original_get_config = model.get_config
    model.get_config = dummy_get_config

    try:
        m = model.load_model(project_dir="dummy_project_dir")

        # Unwrap ObservableModel if present
        real_model = m
        if hasattr(m, "model"):
            real_model = m.model

        # The returned model should be an instance of ClaudeModel (not wrapped)
        assert real_model.__class__.__name__ == "ClaudeModel"

        # The api_key attribute should be set correctly
        # ClaudeModel stores api_key as self.api_key
        assert getattr(real_model, "api_key", None) == dummy_api_key

    finally:
        model.get_config = original_get_config


def test_load_model_returns_none_for_unknown_platform(monkeypatch):
    """
    Test that load_model returns None when platform is unknown.
    """

    def dummy_get_config(project_dir):
        return {
            "platform": "unknown_platform_xyz",
            "api_key": "irrelevant",
        }

    original_get_config = model.get_config
    model.get_config = dummy_get_config

    try:
        m = model.load_model(project_dir="dummy_project_dir")
        # If wrapped by ObservableModel, unwrap
        if m is not None and hasattr(m, "model"):
            m = m.model
        assert m is None
    finally:
        model.get_config = original_get_config