import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_reproduces_bug_and_passes_after_patch():
    # Use environment variables for API key and base URL
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    # Initialize the formatter with environment variables
    formatter = DashScopeChatFormatter(api_key=api_key, base_url=base_url)

    # Prepare input that triggers the bug
    input_text = "Test input that previously caused formatting issues"

    # Call the async method that was buggy
    output = await formatter.format(input_text)

    # Assert expected output after patch (example assertion)
    expected_output = "Expected formatted output after patch"
    assert output == expected_output