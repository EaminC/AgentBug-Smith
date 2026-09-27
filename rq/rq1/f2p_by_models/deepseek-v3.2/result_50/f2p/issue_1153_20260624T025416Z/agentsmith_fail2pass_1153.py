import os
import pytest
from unittest.mock import patch, MagicMock
from gpt_engineer.core.ai import AI


def test_azure_deployment_name_used_as_deployment_name():
    """
    When Azure endpoint is provided, the model_name should be passed as deployment_name
    to AzureChatOpenAI, not as model_name.
    """
    ai = AI(
        model_name="my-deployment",
        azure_endpoint="https://my-resource.openai.azure.com/",
        temperature=0.0,
    )

    with patch("gpt_engineer.core.ai.AzureChatOpenAI") as mock_azure_chat:
        ai._create_chat_model()
        mock_azure_chat.assert_called_once()
        call_kwargs = mock_azure_chat.call_args[1]

        # In the buggy code, deployment_name is set to model_name, but the bug is that
        # the model_name is also incorrectly used as model parameter somewhere else.
        # The fix ensures deployment_name is correctly used.
        assert call_kwargs["deployment_name"] == "my-deployment"
        # Ensure model_name is NOT passed (AzureChatOpenAI doesn't accept model_name)
        assert "model_name" not in call_kwargs


def test_azure_endpoint_without_model_name_fallback():
    """
    If azure_endpoint is set but model_name is empty, deployment_name should be empty.
    """
    ai = AI(
        model_name="",
        azure_endpoint="https://my-resource.openai.azure.com/",
        temperature=0.0,
    )

    with patch("gpt_engineer.core.ai.AzureChatOpenAI") as mock_azure_chat:
        ai._create_chat_model()
        mock_azure_chat.assert_called_once()
        call_kwargs = mock_azure_chat.call_args[1]
        assert call_kwargs["deployment_name"] == ""
        assert "model_name" not in call_kwargs


def test_non_azure_model_name_passed_correctly():
    """
    For non-Azure (standard OpenAI) the model_name should be passed as model_name to ChatOpenAI.
    """
    ai = AI(
        model_name="gpt-4",
        temperature=0.0,
    )

    with patch("gpt_engineer.core.ai.ChatOpenAI") as mock_chat:
        ai._create_chat_model()
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        # ChatOpenAI uses 'model' parameter, not 'model_name'
        assert call_kwargs["model"] == "gpt-4"
        assert "deployment_name" not in call_kwargs


def test_azure_openai_api_version_default():
    """
    Ensure the default OPENAI_API_VERSION is correct (2024-05-01-preview after fix).
    """
    # Temporarily delete env var to test default
    original = os.environ.pop("OPENAI_API_VERSION", None)
    try:
        ai = AI(
            model_name="my-deployment",
            azure_endpoint="https://my-resource.openai.azure.com/",
            temperature=0.0,
        )
        with patch("gpt_engineer.core.ai.AzureChatOpenAI") as mock_azure_chat:
            ai._create_chat_model()
            mock_azure_chat.assert_called_once()
            call_kwargs = mock_azure_chat.call_args[1]
            # After fix, default should be "2024-05-01-preview"
            assert call_kwargs["openai_api_version"] == "2024-05-01-preview"
    finally:
        if original is not None:
            os.environ["OPENAI_API_VERSION"] = original


def test_azure_openai_api_version_from_env():
    """
    Ensure OPENAI_API_VERSION environment variable is respected.
    """
    os.environ["OPENAI_API_VERSION"] = "2023-12-01-preview"
    try:
        ai = AI(
            model_name="my-deployment",
            azure_endpoint="https://my-resource.openai.azure.com/",
            temperature=0.0,
        )
        with patch("gpt_engineer.core.ai.AzureChatOpenAI") as mock_azure_chat:
            ai._create_chat_model()
            mock_azure_chat.assert_called_once()
            call_kwargs = mock_azure_chat.call_args[1]
            assert call_kwargs["openai_api_version"] == "2023-12-01-preview"
    finally:
        del os.environ["OPENAI_API_VERSION"]
