import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for API keys if needed
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter()

    # Prepare a sample chat message input
    chat_message = {
        "role": "user",
        "content": "Hello, how are you?"
    }

    # Format the chat message
    formatted = formatter.format(chat_message)
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Parse the formatted message back
    parsed = formatter.parse(formatted)
    assert isinstance(parsed, dict)
    assert parsed.get("role") == "user"
    assert "Hello, how are you?" in parsed.get("content", "")

    # Test async method if exists (example)
    if hasattr(formatter, "format_async"):
        formatted_async = await formatter.format_async(chat_message)
        assert isinstance(formatted_async, str)
        assert "Hello, how are you?" in formatted_async

    if hasattr(formatter, "parse_async"):
        parsed_async = await formatter.parse_async(formatted_async)
        assert isinstance(parsed_async, dict)
        assert parsed_async.get("role") == "user"
        assert "Hello, how are you?" in parsed_async.get("content", "")