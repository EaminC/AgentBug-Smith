import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.fixture
def formatter():
    # Use environment variables for any keys if needed inside formatter init
    return DashScopeChatFormatter()

def test_dashscope_formatter_basic(formatter):
    # Basic test to check formatting output is as expected
    input_text = "Hello, world!"
    formatted = formatter.format(input_text)
    assert isinstance(formatted, str)
    assert "Hello" in formatted

def test_dashscope_formatter_handles_empty_input(formatter):
    # Test that empty input returns empty or expected output without error
    formatted = formatter.format("")
    assert formatted == "" or formatted is not None

def test_dashscope_formatter_integration(formatter):
    # Integration style test: format a multi-line input and check output structure
    input_text = "Line1\nLine2\nLine3"
    formatted = formatter.format(input_text)
    assert formatted.count("\n") >= 2
    assert "Line1" in formatted and "Line3" in formatted

@pytest.mark.asyncio
async def test_dashscope_formatter_async_behavior(formatter):
    # If formatter has async methods, test them properly awaited
    if hasattr(formatter, "format_async"):
        result = await formatter.format_async("async test")
        assert isinstance(result, str)
        assert "async" in result