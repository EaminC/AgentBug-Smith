import os
import pytest
import asyncio

from agentscope.formatter import DashScopeChatFormatter


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_formatting():
    # Use environment variables for model and API key
    model_name = os.getenv("MODEL", "tensorblock/gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Prepare a sample chat message input
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Call the async format method and await result
    formatted_output = await formatter.format(messages)

    # Assert the output contains expected keys or substrings
    assert isinstance(formatted_output, str)
    assert "Hello" in formatted_output or "hello" in formatted_output.lower()
    assert "assistant" not in formatted_output.lower()  # The output should be user-facing text, not role labels


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_handles_empty_messages():
    model_name = os.getenv("MODEL", "tensorblock/gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Empty messages list should not raise, but return empty or default string
    formatted_output = await formatter.format([])

    assert isinstance(formatted_output, str)
    # Could be empty string or some default message
    assert formatted_output is not None


@pytest.mark.asyncio
async def test_dashscope_chat_formatter_formatting_with_multiple_messages():
    model_name = os.getenv("MODEL", "tensorblock/gpt-4.1-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    formatter = DashScopeChatFormatter(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather today?"},
        {"role": "assistant", "content": "The weather is sunny."},
        {"role": "user", "content": "Thank you!"},
    ]

    formatted_output = await formatter.format(messages)

    assert isinstance(formatted_output, str)
    assert "weather" in formatted_output.lower()
    assert "sunny" in formatted_output.lower()