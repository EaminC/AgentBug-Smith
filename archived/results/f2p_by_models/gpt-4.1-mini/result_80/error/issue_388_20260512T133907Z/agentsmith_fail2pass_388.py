import os
import pytest
from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_formatter_basic_usage():
    # Initialize formatter with environment variable for API key
    formatter = DashScopeChatFormatter(api_key=os.getenv("OPENAI_API_KEY"))

    # Prepare a sample chat message list
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format the messages asynchronously
    formatted = await formatter.format(messages)

    # Assert the formatted output contains expected keys and content
    assert isinstance(formatted, str)
    assert "Hello" in formatted or "hello" in formatted.lower()
    assert "assistant" not in formatted.lower()  # The formatter output should be user-facing text

    # Additional checks can be added here based on formatter behavior


@pytest.mark.asyncio
async def test_dashscope_formatter_handles_empty_messages():
    formatter = DashScopeChatFormatter(api_key=os.getenv("OPENAI_API_KEY"))
    formatted = await formatter.format([])
    assert formatted == "" or formatted is None


@pytest.mark.asyncio
async def test_dashscope_formatter_invalid_api_key():
    # Use an invalid API key to check error handling
    formatter = DashScopeChatFormatter(api_key="invalid_key")
    messages = [{"role": "user", "content": "Test message"}]

    with pytest.raises(Exception):
        await formatter.format(messages)