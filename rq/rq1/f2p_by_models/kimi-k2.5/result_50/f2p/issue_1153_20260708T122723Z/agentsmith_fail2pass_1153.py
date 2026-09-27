import os

import pytest

from gpt_engineer.core.ai import AI


class MockAzureChatOpenAI:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs


def test_azure_openai_default_api_version(monkeypatch):
    """Test that Azure OpenAI uses the correct default API version.
    
    This tests the fix for issue #1153 where the deployment name was being
    mixed up with the model name due to using an outdated API version.
    """
    # Ensure OPENAI_API_VERSION is not set so we test the default
    monkeypatch.delenv("OPENAI_API_VERSION", raising=False)
    
    # Mock AzureChatOpenAI to capture initialization arguments
    monkeypatch.setattr("gpt_engineer.core.ai.AzureChatOpenAI", MockAzureChatOpenAI)
    
    # Create AI instance with Azure endpoint
    ai = AI(
        model_name="test-deployment",
        azure_endpoint="https://test.openai.azure.com/",
        streaming=False
    )
    
    # Create the chat model
    model = ai._create_chat_model()
    
    # Verify AzureChatOpenAI was called with correct API version
    # The fix changes the default from "2023-05-15" to "2024-05-01-preview"
    assert model.init_kwargs["openai_api_version"] == "2024-05-01-preview", \
        f"Expected API version '2024-05-01-preview', got '{model.init_kwargs['openai_api_version']}'"
    
    # Verify other important parameters are passed correctly
    assert model.init_kwargs["azure_endpoint"] == "https://test.openai.azure.com/"
    assert model.init_kwargs["deployment_name"] == "test-deployment"
    assert model.init_kwargs["openai_api_type"] == "azure"
