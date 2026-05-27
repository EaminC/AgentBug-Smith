import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for any keys if needed by the formatter (none needed here)
    formatter = DashScopeChatFormatter()

    # Example input message to format
    input_message = {
        "role": "user",
        "content": "Hello, how are you?"
    }

    # Format the message using the formatter
    formatted = formatter.format(input_message)

    # The formatted output should be a string containing the original content
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Now parse back the formatted string
    parsed = formatter.parse(formatted)

    # The parsed output should be a dict with keys 'role' and 'content'
    assert isinstance(parsed, dict)
    assert parsed.get("role") == "user"
    assert "Hello, how are you?" in parsed.get("content", "")

    # Test async method if exists (assuming async parse or format)
    if hasattr(formatter, "format_async"):
        formatted_async = await formatter.format_async(input_message)
        assert isinstance(formatted_async, str)
        assert "Hello, how are you?" in formatted_async

    if hasattr(formatter, "parse_async"):
        parsed_async = await formatter.parse_async(formatted)
        assert isinstance(parsed_async, dict)
        assert parsed_async.get("role") == "user"
        assert "Hello, how are you?" in parsed_async.get("content", "")