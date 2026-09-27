import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_reproduction_and_fix():
    # Initialize formatter with environment variable for API key
    formatter = DashScopeChatFormatter(api_key=os.getenv("OPENAI_API_KEY"))

    # Prepare input that triggers the original bug
    input_text = "Test input that previously caused formatting bug"

    # Call the async method that was buggy
    output = await formatter.format_chat(input_text)

    # Assert output is as expected after the patch (example assertion)
    assert output is not None
    assert "formatted" in output.lower()
    assert len(output) > 0