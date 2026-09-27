import unittest.mock

import openai
import pytest

import strands
from strands.models.openai import OpenAIModel
from strands.types.exceptions import ContextWindowOverflowException


@pytest.fixture
def openai_client():
    with unittest.mock.patch.object(strands.models.openai.openai, "AsyncOpenAI") as mock_client_cls:
        mock_client = unittest.mock.AsyncMock()
        # Make the mock client work as an async context manager
        mock_client.__aenter__ = unittest.mock.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = unittest.mock.AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def model_id():
    return "m1"


@pytest.fixture
def model(openai_client, model_id):
    _ = openai_client

    return OpenAIModel(model_id=model_id, params={"max_tokens": 1})


@pytest.fixture
def messages():
    return [{"role": "user", "content": [{"text": "test"}]}]


@pytest.fixture
def test_output_model_cls():
    import pydantic

    class TestOutputModel(pydantic.BaseModel):
        name: str
        age: int

    return TestOutputModel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        "Input is too long for requested model",
        "input length and `max_tokens` exceed context limit",
        "too many total text bytes",
    ],
)
async def test_stream_alternative_context_overflow_messages(openai_client, model, messages, error_message):
    """Test that alternative context overflow messages in APIError are properly converted."""
    # Create a mock OpenAI APIError with alternative context overflow message
    mock_error = openai.APIError(
        message=error_message,
        request=unittest.mock.MagicMock(),
        body={"error": {"message": error_message}},
    )

    # Configure the mock client to raise the APIError
    openai_client.chat.completions.create.side_effect = mock_error

    # Test that the stream method converts the error properly
    with pytest.raises(ContextWindowOverflowException) as exc_info:
        async for _ in model.stream(messages):
            pass

    # Verify the exception message contains the original error
    assert error_message in str(exc_info.value)
    assert exc_info.value.__cause__ == mock_error


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        "Input is too long for requested model",
        "input length and `max_tokens` exceed context limit",
        "too many total text bytes",
    ],
)
async def test_structured_output_alternative_context_overflow_messages(
    openai_client, model, messages, test_output_model_cls, error_message
):
    """Test that alternative context overflow messages in APIError are properly converted in structured output."""
    # Create a mock OpenAI APIError with alternative context overflow message
    mock_error = openai.APIError(
        message=error_message,
        request=unittest.mock.MagicMock(),
        body={"error": {"message": error_message}},
    )

    # Configure the mock client to raise the APIError
    openai_client.beta.chat.completions.parse.side_effect = mock_error

    # Test that the structured_output method converts the error properly
    with pytest.raises(ContextWindowOverflowException) as exc_info:
        async for _ in model.structured_output(test_output_model_cls, messages):
            pass

    # Verify the exception message contains the original error
    assert error_message in str(exc_info.value)
    assert exc_info.value.__cause__ == mock_error


@pytest.mark.asyncio
async def test_stream_api_error_passthrough(openai_client, model, messages):
    """Test that APIError without overflow messages passes through unchanged."""
    # Create a mock OpenAI APIError without overflow message
    mock_error = openai.APIError(
        message="Some other API error",
        request=unittest.mock.MagicMock(),
        body={"error": {"message": "Some other API error"}},
    )

    # Configure the mock client to raise the APIError
    openai_client.chat.completions.create.side_effect = mock_error

    # Test that APIError without overflow messages passes through
    with pytest.raises(openai.APIError) as exc_info:
        async for _ in model.stream(messages):
            pass

    # Verify the original exception is raised, not ContextWindowOverflowException
    assert exc_info.value == mock_error
