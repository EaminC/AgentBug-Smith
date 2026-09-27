import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_reproduction_and_fix():
    # Use environment variables for API keys
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY environment variable must be set"

    # Initialize the formatter with environment-based config
    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
        model=os.getenv("MODEL", "tensorblock/gpt-4.1-mini"),
    )

    # Prepare a sample input that triggers the bug
    input_text = "Test input that previously caused the bug"

    # Run the formatter asynchronously and get the output
    output = await formatter.format(input_text)

    # Assert expected output properties after the bug fix
    assert output is not None
    assert isinstance(output, str)
    assert "expected substring or pattern" in output.lower()