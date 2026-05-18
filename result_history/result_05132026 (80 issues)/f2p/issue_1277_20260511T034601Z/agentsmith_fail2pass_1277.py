import unittest
from unittest.mock import AsyncMock, patch
from agentscope.model import DashScopeChatModel
from agentscope.message import TextBlock


class TestDashScopeChatModelMultimodal(unittest.IsolatedAsyncioTestCase):
    async def test_multimodal_model_uses_async_call(self):
        model = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key="test_key",
            stream=False,
            multimodality=True,
        )
        messages = [{"role": "user", "content": "Describe this image."}]

        # Prepare a mock response object with expected attributes
        class MockMessage(dict):
            def __init__(self, content):
                super().__init__({"content": content})
                self.content = content
                self.tool_calls = None

        class MockChoice:
            def __init__(self, message):
                self.message = message

        class MockOutput:
            def __init__(self, choices):
                self.choices = choices

        class MockResponse:
            def __init__(self, status_code, content):
                self.status_code = status_code
                self.output = MockOutput([MockChoice(MockMessage(content))])
                self.usage = None
                self.request_id = "dummy"
                self.code = None
                self.message = None

        mock_response = MockResponse(200, "This is a test image.")

        with patch(
            "dashscope.AioMultiModalConversation.call",
            new_callable=AsyncMock,
        ) as mock_call:
            mock_call.return_value = mock_response
            result = await model(messages)
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            self.assertEqual(call_kwargs["messages"], messages)
            self.assertEqual(call_kwargs["model"], "qwen-vl-plus")
            # The result should have content with a TextBlock containing the response text
            self.assertTrue(hasattr(result, "content"))
            self.assertIsInstance(result.content, list)
            self.assertTrue(
                any(
                    isinstance(block, dict) and block.get("type") == "text" and block.get("text") == "This is a test image."
                    for block in result.content
                )
            )


if __name__ == "__main__":
    unittest.main()
