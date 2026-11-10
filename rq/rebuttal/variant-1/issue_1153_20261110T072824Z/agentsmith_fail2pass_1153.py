import os
import pytest

from gpt_engineer.core.ai import AI


@pytest.mark.parametrize(
    "openai_api_version_env,expected_version",
    [
        ("2023-05-15", "2024-05-01-preview"),  # buggy fallback replaced by fixed version
        ("2024-05-01-preview", "2024-05-01-preview"),
        ("", "2024-05-01-preview"),
    ],
)
def test_openai_api_version_env(monkeypatch, openai_api_version_env, expected_version):
    """
    Test that the openai_api_version used in AzureChatOpenAI is always the fixed
    '2024-05-01-preview' regardless of environment variable fallback.

    This test will fail on the buggy codebase because it falls back to '2023-05-15'.
    After the fix, it should pass with '2024-05-01-preview'.
    """

    if openai_api_version_env:
        monkeypatch.setenv("OPENAI_API_VERSION", openai_api_version_env)
    else:
        monkeypatch.delenv("OPENAI_API_VERSION", raising=False)

    ai = AI(
        model_name="deployment",
        azure_endpoint="https://fake-azure-endpoint.openai.azure.com/",
        streaming=False,
    )
    chat_model = ai._create_chat_model()

    assert chat_model.openai_api_version == expected_version
