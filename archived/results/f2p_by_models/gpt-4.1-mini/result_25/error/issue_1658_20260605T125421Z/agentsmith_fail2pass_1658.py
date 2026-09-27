import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_formatting():
    # Use environment variables for model keys
    openai_api_key = os.getenv("OPENAI_API_KEY")
    assert openai_api_key is not None, "OPENAI_API_KEY env var must be set"

    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        model=os.getenv("MODEL", "tensorblock/gpt-4.1-mini"),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Prepare a sample chat input to test formatting
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Call the async format method and await result
    formatted_output = await formatter.format(chat_input)

    # Assert the formatted output contains expected keys and strings
    assert isinstance(formatted_output, str)
    assert "Hello" in formatted_output or "hello" in formatted_output.lower()
    assert "assistant" in formatted_output.lower() or "system" in formatted_output.lower()