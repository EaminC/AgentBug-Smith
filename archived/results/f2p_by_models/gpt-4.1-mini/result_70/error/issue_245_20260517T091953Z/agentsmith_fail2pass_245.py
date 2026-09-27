import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for any API keys if needed (example)
    openai_key = os.getenv("OPENAI_API_KEY")
    assert openai_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter()

    # Prepare a sample chat message to format
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]

    # Format messages
    formatted = formatter.format(messages)
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Parse the formatted string back to messages
    parsed = formatter.parse(formatted)
    assert isinstance(parsed, list)
    assert any(m.get("content") == "Hello, how are you?" for m in parsed)

    # Test async method if exists (example)
    if hasattr(formatter, "format_async"):
        formatted_async = await formatter.format_async(messages)
        assert isinstance(formatted_async, str)
        assert "Hello, how are you?" in formatted_async

    if hasattr(formatter, "parse_async"):
        parsed_async = await formatter.parse_async(formatted_async)
        assert isinstance(parsed_async, list)
        assert any(m.get("content") == "Hello, how are you?" for m in parsed_async)