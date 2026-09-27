import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_format_and_parse():
    # Use environment variables for API keys and base URLs
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        temperature=0.7,
    )

    # Prepare a sample message input
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format messages to prompt string
    prompt = formatter.format(messages)
    assert isinstance(prompt, str)
    assert "You are a helpful assistant." in prompt
    assert "Hello, how are you?" in prompt

    # Simulate a response string from the model
    response_str = "I'm fine, thank you!"

    # Parse the response string back to message format
    parsed_messages = formatter.parse(response_str)
    assert isinstance(parsed_messages, list)
    assert any("I'm fine" in msg.get("content", "") for msg in parsed_messages)