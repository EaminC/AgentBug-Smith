import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for keys and URLs
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        temperature=0.7,
    )

    # Sample input message to format
    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]

    # Format the messages
    formatted = await formatter.format(messages)

    # The formatted output should be a string containing the user message
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Parse the formatted string back to messages
    parsed = await formatter.parse(formatted)

    # The parsed output should be a list of messages
    assert isinstance(parsed, list)
    assert any(m.get("content") == "Hello, how are you?" for m in parsed)