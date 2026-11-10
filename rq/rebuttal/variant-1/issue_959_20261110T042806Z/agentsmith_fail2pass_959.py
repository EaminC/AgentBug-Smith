import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_runs_and_formats_correctly():
    # Use environment variables for any keys or config needed
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY environment variable must be set"

    formatter = DashScopeChatFormatter(api_key=api_key, temperature=0.7)

    # Prepare a sample chat input to trigger the formatter
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ]

    # The formatter likely has an async method to format or generate a response
    # Await the coroutine properly
    formatted_output = await formatter.format_chat(chat_input)

    # Assert the output is a non-empty string (adjust assertions to match actual expected behavior)
    assert isinstance(formatted_output, str)
    assert len(formatted_output) > 0
    assert "Hello" in formatted_output or "hello" in formatted_output.lower()