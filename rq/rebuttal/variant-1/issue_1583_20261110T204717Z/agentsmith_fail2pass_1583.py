import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_formatting():
    # Initialize formatter with environment variables for keys
    formatter = DashScopeChatFormatter(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        model=os.getenv("MODEL", "openrouter3/openai/gpt-4.1-mini"),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Prepare a sample chat input to format
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format the chat input using the formatter
    formatted_output = await formatter.format(chat_input)

    # Assert that the formatted output contains expected keys and structure
    assert isinstance(formatted_output, str)
    assert "Hello, how are you?" in formatted_output
    assert "You are a helpful assistant." in formatted_output