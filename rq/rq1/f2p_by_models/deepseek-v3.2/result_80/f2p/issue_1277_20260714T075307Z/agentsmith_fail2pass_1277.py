from typing import Any, AsyncGenerator
from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from http import HTTPStatus
from pydantic import BaseModel

from agentscope.model import DashScopeChatModel, ChatResponse
from agentscope.message import TextBlock


class MessageMock(dict):
    """Mock class for message objects, supports both dictionary and
    attribute access."""

    def __init__(self, data: dict[str, Any]):
        super().__init__(data)
        for key, value in data.items():
            setattr(self, key, value)


class TestDashScopeChatModelMultimodalAsync(IsolatedAsyncioTestCase):
    """Test that multimodal model uses async AioMultiModalConversation."""

    def _create_mock_response(self, content: str) -> Mock:
        """Create a standard mock response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.output.choices = [Mock()]
        mock_response.output.choices[0].message = MessageMock(
            {"content": content},
        )
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        return mock_response

    async def test_multimodal_model_uses_async_call(self) -> None:
        """Test that multimodal model uses async AioMultiModalConversation.call.

        In the buggy version, DashScopeChatModel.__call__ uses synchronous
        dashscope.MultiModalConversation.call for multimodal models, which
        blocks the asyncio event loop. After the fix, it should use
        dashscope.AioMultiModalConversation.call (async).
        """
        model = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key="test_key",
            stream=False,
            multimodality=True,
        )
        messages = [{"role": "user", "content": "Describe this image."}]
        mock_response = self._create_mock_response("This is a test image.")

        # Patch the async call that should be used after the fix
        with patch(
            "dashscope.AioMultiModalConversation.call",
            new_callable=AsyncMock,
        ) as mock_async_call:
            mock_async_call.return_value = mock_response
            result = await model(messages)
            # In the buggy version, this call is not awaited (sync call),
            # so mock_async_call would not be called.
            # In the fixed version, mock_async_call is awaited.
            mock_async_call.assert_called_once()
            call_kwargs = mock_async_call.call_args[1]
            self.assertEqual(call_kwargs["messages"], messages)
            self.assertEqual(call_kwargs["model"], "qwen-vl-plus")
            self.assertIsInstance(result, ChatResponse)
            self.assertEqual(
                result.content,
                [TextBlock(type="text", text="This is a test image.")],
            )

    async def test_multimodal_model_with_autodetection_async(self) -> None:
        """Test that model name containing '-vl' triggers async multimodal call."""
        model = DashScopeChatModel(
            model_name="qwen-vl-max",
            api_key="test_key",
            stream=False,
            # multimodality is not set, should be auto-detected
        )
        messages = [{"role": "user", "content": "What's in the picture?"}]
        mock_response = self._create_mock_response("A cat.")

        with patch(
            "dashscope.AioMultiModalConversation.call",
            new_callable=AsyncMock,
        ) as mock_async_call:
            mock_async_call.return_value = mock_response
            result = await model(messages)
            # In buggy version, this would call sync MultiModalConversation.call
            # and mock_async_call would not be invoked.
            mock_async_call.assert_called_once()
            call_kwargs = mock_async_call.call_args[1]
            self.assertEqual(call_kwargs["messages"], messages)
            self.assertEqual(call_kwargs["model"], "qwen-vl-max")
            self.assertIsInstance(result, ChatResponse)
            self.assertEqual(
                result.content,
                [TextBlock(type="text", text="A cat.")],
            )

    async def test_multimodal_streaming_async(self) -> None:
        """Test multimodal streaming uses async generator."""
        model = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key="test_key",
            stream=True,
            multimodality=True,
        )
        messages = [{"role": "user", "content": "Stream describe."}]

        # Create a mock async generator
        mock_chunk = Mock()
        mock_chunk.status_code = HTTPStatus.OK
        mock_chunk.output.choices = [Mock()]
        mock_chunk.output.choices[0].message = MessageMock(
            {"content": "chunk1", "reasoning_content": "", "tool_calls": []},
        )
        mock_chunk.usage = Mock()
        mock_chunk.usage.input_tokens = 5
        mock_chunk.usage.output_tokens = 10

        async def async_gen():
            yield mock_chunk

        with patch(
            "dashscope.AioMultiModalConversation.call",
            new_callable=AsyncMock,
        ) as mock_async_call:
            mock_async_call.return_value = async_gen()
            result = await model(messages)
            # In buggy version, sync call returns a sync generator,
            # causing the test to hang or fail.
            mock_async_call.assert_called_once()
            # Ensure result is async iterable
            responses = []
            async for response in result:
                responses.append(response)
            self.assertEqual(len(responses), 1)
            self.assertIsInstance(responses[0], ChatResponse)

    async def test_multimodal_explicit_false_uses_generation(self) -> None:
        """Test that explicit multimodality=False uses generation API."""
        model = DashScopeChatModel(
            model_name="qwen-vl-plus",  # name suggests multimodal
            api_key="test_key",
            stream=False,
            multimodality=False,  # explicitly disable
        )
        messages = [{"role": "user", "content": "Hello"}]
        mock_response = self._create_mock_response("Hi")

        # Should call AioGeneration.call, not AioMultiModalConversation.call
        with patch(
            "dashscope.aigc.generation.AioGeneration.call",
            new_callable=AsyncMock,
        ) as mock_gen_call:
            mock_gen_call.return_value = mock_response
            with patch(
                "dashscope.AioMultiModalConversation.call",
                new_callable=AsyncMock,
            ) as mock_mm_call:
                result = await model(messages)
                mock_gen_call.assert_called_once()
                mock_mm_call.assert_not_called()
                self.assertIsInstance(result, ChatResponse)
                self.assertEqual(
                    result.content,
                    [TextBlock(type="text", text="Hi")],
                )
