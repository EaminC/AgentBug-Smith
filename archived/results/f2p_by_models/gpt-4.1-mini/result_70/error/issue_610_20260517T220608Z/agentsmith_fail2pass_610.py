import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_reproduction_and_fix():
    # Use environment variables for API key and base URL
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    # Initialize the formatter with environment variables
    formatter = DashScopeChatFormatter(api_key=api_key, base_url=base_url)

    # Prepare input that triggers the bug
    input_text = "Test input that previously caused a bug"

    # Call the method that had the bug (assuming async)
    output = await formatter.format(input_text)

    # Assert expected output after the patch
    expected_output = "Expected formatted output after bug fix"
    assert output == expected_output