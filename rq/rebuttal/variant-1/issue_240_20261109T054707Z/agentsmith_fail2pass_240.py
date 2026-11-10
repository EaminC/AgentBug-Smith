import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_runs_and_formats_correctly():
    # Initialize formatter with environment variable for any keys if needed
    formatter = DashScopeChatFormatter()

    # Example input to formatter (adapted from in-patch test)
    input_data = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
    }

    # Call the async format method and await result
    formatted_output = await formatter.format(input_data)

    # Assert output contains expected keys or substrings (from original patch tests)
    assert isinstance(formatted_output, str)
    assert "Hello, world!" in formatted_output
    assert "system" not in formatted_output.lower()  # assuming formatter removes role labels

    # Additional assertions from patch tests can be added here if available