import os
import pytest
from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Initialize formatter with environment variable for API key
    formatter = DashScopeChatFormatter(api_key=os.getenv("OPENAI_API_KEY"))

    # Prepare a sample chat message input
    chat_input = {
        "role": "user",
        "content": "Hello, how are you?"
    }

    # Format the chat input
    formatted = formatter.format(chat_input)
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Parse the formatted output back
    parsed = formatter.parse(formatted)
    assert isinstance(parsed, dict)
    assert parsed.get("role") == "user"
    assert "Hello, how are you?" in parsed.get("content", "")

    # If the formatter has async methods, test them as well
    if hasattr(formatter, "format_async"):
        formatted_async = await formatter.format_async(chat_input)
        assert isinstance(formatted_async, str)
        assert "Hello, how are you?" in formatted_async

    if hasattr(formatter, "parse_async"):
        parsed_async = await formatter.parse_async(formatted_async)
        assert isinstance(parsed_async, dict)
        assert parsed_async.get("role") == "user"
        assert "Hello, how are you?" in parsed_async.get("content", "")