import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_formatting():
    # Use environment variables for keys if needed (example)
    openai_key = os.getenv("OPENAI_API_KEY")
    assert openai_key is not None, "OPENAI_API_KEY must be set in environment"

    formatter = DashScopeChatFormatter()

    # Example input and expected output based on the original test patch
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # The formatter should produce a formatted string or list of strings
    formatted = await formatter.format(messages)

    # Assert the formatted output contains expected substrings or structure
    assert isinstance(formatted, str) or isinstance(formatted, list)
    assert "You are a helpful assistant." in (formatted if isinstance(formatted, str) else " ".join(formatted))
    assert "Hello, how are you?" in (formatted if isinstance(formatted, str) else " ".join(formatted))