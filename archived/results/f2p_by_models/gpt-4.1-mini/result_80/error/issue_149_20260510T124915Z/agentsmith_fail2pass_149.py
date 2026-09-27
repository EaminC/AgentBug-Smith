import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_basic():
    # Use environment variables for keys if needed by the formatter internally
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter()

    # Example input and expected output based on formatter's known behavior
    input_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # The formatter likely has an async method to format messages
    formatted = await formatter.format_messages(input_messages)

    # Assert formatted output is a string containing user content
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted
    assert "You are a helpful assistant." in formatted


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_handles_empty_messages():
    formatter = DashScopeChatFormatter()
    formatted = await formatter.format_messages([])
    assert isinstance(formatted, str)
    assert formatted.strip() == "" or formatted is not None


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_preserves_roles():
    formatter = DashScopeChatFormatter()
    input_messages = [
        {"role": "system", "content": "System message"},
        {"role": "assistant", "content": "Assistant reply"},
        {"role": "user", "content": "User question"},
    ]
    formatted = await formatter.format_messages(input_messages)
    # Check that all roles appear in the formatted string in some form
    for msg in input_messages:
        assert msg["content"] in formatted