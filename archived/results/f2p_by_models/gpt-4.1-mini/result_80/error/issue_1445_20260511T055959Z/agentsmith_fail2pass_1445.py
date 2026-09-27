import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for API keys if needed by formatter internally
    # (Assuming formatter uses environment variables internally for API keys)
    formatter = DashScopeChatFormatter()

    # Prepare a sample chat input to format
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format the chat input
    formatted = await formatter.format(chat_input)
    assert isinstance(formatted, str)
    assert "You are a helpful assistant." in formatted
    assert "Hello, how are you?" in formatted

    # Parse back the formatted string to chat messages
    parsed = await formatter.parse(formatted)
    assert isinstance(parsed, list)
    assert any(msg.get("content") == "You are a helpful assistant." for msg in parsed)
    assert any(msg.get("content") == "Hello, how are you?" for msg in parsed)