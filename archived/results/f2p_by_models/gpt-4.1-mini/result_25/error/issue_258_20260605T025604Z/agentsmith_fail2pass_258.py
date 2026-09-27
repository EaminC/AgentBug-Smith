import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_reproduction_and_fix():
    # Use environment variables for API keys and base URLs
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(api_key=openai_api_key, base_url=openai_base_url)

    # Prepare a sample input that triggers the bug
    input_text = "Test input that previously caused the bug"

    # Call the async method that was buggy
    result = await formatter.format_chat(input_text)

    # Assert expected output after the patch
    assert result is not None
    assert isinstance(result, str)
    assert "expected substring" in result.lower()