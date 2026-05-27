import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_fix():
    # Use environment variables for keys and URLs
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    # Initialize formatter with environment variables
    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
    )

    # Prepare input that previously triggered the bug
    input_text = "Test input that triggers the bug"

    # Call the async method that was buggy
    result = await formatter.format_chat(input_text)

    # Assert expected output after the patch
    assert isinstance(result, str)
    assert "expected substring" in result.lower()