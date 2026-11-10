import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_runs_and_formats_correctly():
    # Initialize formatter with environment variables for API keys
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter(
        model=os.getenv("MODEL", "openrouter2/openai/gpt-4.1-mini"),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
        openai_api_key=api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
    )

    # Prepare a sample chat input to format
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Run the formatter asynchronously and get the formatted output
    formatted_output = await formatter.format(chat_input)

    # Assert the formatted output is a non-empty string
    assert isinstance(formatted_output, str)
    assert len(formatted_output) > 0

    # Optionally check that the output contains expected substrings
    assert "Hello" in formatted_output or "hello" in formatted_output.lower()