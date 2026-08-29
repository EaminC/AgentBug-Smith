import os
import pytest
from agentscope.formatter import DashScopeChatFormatter

@pytest.mark.asyncio
async def test_dashscope_formatter_corrects_bug():
    # Initialize formatter with environment variables
    formatter = DashScopeChatFormatter(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        anthropic_api_key=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL"),
        model=os.getenv("MODEL"),
        temperature=float(os.getenv("AI_TEMPERATURE", "0.7")),
    )

    # Prepare input that triggers the bug
    input_text = "Test input that previously caused formatting issues."

    # Call the formatter asynchronously and get output
    output = await formatter.format(input_text)

    # Assert the output is as expected after the patch
    assert output is not None
    assert "corrected" in output.lower() or "fixed" in output.lower()