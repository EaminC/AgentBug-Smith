import asyncio
import pytest
from google import genai
from strands.models.gemini import GeminiModel
from strands.types.exceptions import ModelThrottledException


@pytest.mark.asyncio
async def test_vertex_ai_429_plain_text_message_converts_to_model_throttled_exception():
    """
    Regression test for issue #3226:
    When Vertex AI returns a 429 with a plain-text error message (not JSON),
    GeminiModel.stream() should convert it to ModelThrottledException.
    """
    error = genai.errors.ClientError(
        429,
        {"error": {"status": "RESOURCE_EXHAUSTED", "message": "Resource exhausted. Please try again later."}},
    )
    assert error.code == 429
    assert error.status == "RESOURCE_EXHAUSTED"

    model = GeminiModel(model_id="gemini-2.5-flash", client_args={"api_key": "test"})

    # Patch the client's generate_content_stream to raise the above error
    # We do not mock GeminiModel.stream itself, only the internal client call
    # so that the real stream method runs and triggers the error handling.
    # Use unittest.mock.AsyncMock for the aio.models.generate_content_stream method.
    import unittest.mock

    with unittest.mock.patch.object(genai.Client, "aio", new_callable=unittest.mock.PropertyMock) as aio_mock:
        mock_aio = unittest.mock.AsyncMock()
        aio_mock.return_value = mock_aio
        mock_aio.models.generate_content_stream.side_effect = error

        # The stream method returns an async generator; calling __anext__ triggers the call
        stream_gen = model.stream([{"role": "user", "content": [{"text": "hi"}]}])
        with pytest.raises(ModelThrottledException) as excinfo:
            await stream_gen.__anext__()

        # The exception message should include the plain text message
        assert "Resource exhausted. Please try again later." in str(excinfo.value)
