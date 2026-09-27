import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Initialize formatter with environment variables for model and temperature
    model = os.getenv("MODEL", "tensorblock/gpt-4.1-mini")
    temperature = float(os.getenv("AI_TEMPERATURE", "0.7"))
    formatter = DashScopeChatFormatter(model=model, temperature=temperature)

    # Prepare a sample chat input
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]

    # Format the chat input
    formatted = await formatter.format(chat_input)
    assert isinstance(formatted, str)
    assert "Hello" in formatted

    # Parse the formatted output back to chat messages
    parsed = await formatter.parse(formatted)
    assert isinstance(parsed, list)
    assert any(msg.get("content") and "Hello" in msg["content"] for msg in parsed)