import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_basic():
    # Initialize formatter with environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter(api_key=api_key)

    # Prepare a sample input that triggers the bug fix scenario
    input_text = "Test input to reproduce bug and verify patch"

    # Call the async method that was buggy
    result = await formatter.format(input_text)

    # Assert expected output after patch
    assert result is not None
    assert isinstance(result, str)
    assert "expected substring" in result.lower()  # Replace with actual expected behavior

@pytest.mark.asyncio
async def test_dashscope_formatter_handles_empty_input():
    api_key = os.getenv("OPENAI_API_KEY")
    formatter = DashScopeChatFormatter(api_key=api_key)

    result = await formatter.format("")

    assert result is not None
    assert isinstance(result, str)
    assert result.strip() != ""

@pytest.mark.asyncio
async def test_dashscope_formatter_async_behavior():
    api_key = os.getenv("OPENAI_API_KEY")
    formatter = DashScopeChatFormatter(api_key=api_key)

    # Test multiple concurrent calls to ensure async correctness
    inputs = [f"input {i}" for i in range(5)]
    tasks = [formatter.format(text) for text in inputs]
    results = await asyncio.gather(*tasks)

    for res in results:
        assert res is not None
        assert isinstance(res, str)