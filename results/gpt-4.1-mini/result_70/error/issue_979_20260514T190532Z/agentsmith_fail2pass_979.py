import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_basic():
    # Initialize formatter with environment variables for keys
    formatter = DashScopeChatFormatter(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    # Compose a simple chat message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Format the chat messages
    formatted = formatter.format_chat(messages)

    # Assert formatted output contains expected keys and structure
    assert isinstance(formatted, dict)
    assert "messages" in formatted
    assert isinstance(formatted["messages"], list)
    assert any("role" in msg and "content" in msg for msg in formatted["messages"])

@pytest.mark.asyncio
async def test_dashscope_chat_formatter_async_response():
    formatter = DashScopeChatFormatter(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke."},
    ]

    # Await the async method that generates a response (assuming such method exists)
    response = await formatter.generate_response_async(messages)

    # Validate response is a non-empty string
    assert isinstance(response, str)
    assert len(response) > 0