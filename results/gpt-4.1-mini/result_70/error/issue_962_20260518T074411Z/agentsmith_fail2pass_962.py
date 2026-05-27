import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.fixture
def formatter():
    # Use environment variables for API key and base URL
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("MODEL", "tensorblock/gpt-4.1-mini")
    temperature = float(os.getenv("AI_TEMPERATURE", "0.7"))
    return DashScopeChatFormatter(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
    )

def test_dashscope_formatter_format_and_parse(formatter):
    # Prepare input message
    input_message = "Hello, how are you?"
    # Format the message
    formatted = formatter.format(input_message)
    assert isinstance(formatted, str)
    assert input_message in formatted

    # Simulate a response that the formatter would parse
    response = f"Response: {input_message}"
    parsed = formatter.parse(response)
    assert isinstance(parsed, str)
    assert input_message in parsed