import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_bug_reproduction_and_fix():
    # Initialize formatter with environment variables for API keys
    formatter = DashScopeChatFormatter(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    # Compose a sample chat input that previously triggered the bug
    chat_input = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Format this text with dashscope."}
    ]

    # Call the formatter's async method to format the chat
    formatted_output = await formatter.format_chat(chat_input)

    # Assert that the output is a non-empty string and contains expected formatting
    assert isinstance(formatted_output, str)
    assert len(formatted_output) > 0
    assert "dashscope" in formatted_output.lower()