import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_bug_reproduction_and_fix():
    # Use environment variables for keys and URLs
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    # Initialize formatter with environment-based config
    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
    )

    # Prepare input that previously triggered the bug
    input_text = "Test input that triggers the DashScopeChatFormatter bug"

    # Call the async method that was buggy
    output = await formatter.format(input_text)

    # Assert output correctness after patch
    assert output is not None
    assert isinstance(output, str)
    assert "expected substring or pattern" in output.lower()