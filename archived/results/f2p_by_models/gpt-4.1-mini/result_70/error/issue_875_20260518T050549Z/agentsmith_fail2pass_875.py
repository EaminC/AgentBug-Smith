import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for model and API key
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        model=os.getenv("MODEL", "tensorblock/gpt-4.1-mini"),
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Prepare a sample conversation input
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format the messages
    formatted = formatter.format(messages)

    # The formatted output should be a string containing the user message
    assert isinstance(formatted, str)
    assert "Hello, how are you?" in formatted

    # Parse the formatted string back to messages
    parsed = formatter.parse(formatted)

    # The parsed output should be a list of dicts with roles and content
    assert isinstance(parsed, list)
    assert all(isinstance(m, dict) for m in parsed)
    assert any(m.get("role") == "user" and "Hello, how are you?" in m.get("content", "") for m in parsed)