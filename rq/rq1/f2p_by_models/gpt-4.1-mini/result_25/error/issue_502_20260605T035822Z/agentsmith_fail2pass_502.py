import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_runs_and_returns_expected_output():
    # Use environment variables for API keys
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter(api_key=openai_api_key)

    # Prepare a sample input that triggers the bug reproduction scenario
    input_text = "Test input to reproduce bug in DashScopeChatFormatter"

    # Call the async method and await its result
    result = await formatter.format(input_text)

    # Assert that the result is a non-empty string (expected behavior after patch)
    assert isinstance(result, str)
    assert len(result) > 0