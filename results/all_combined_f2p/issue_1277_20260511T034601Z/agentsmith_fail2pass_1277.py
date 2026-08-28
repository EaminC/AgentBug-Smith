import sys
from unittest.mock import AsyncMock, MagicMock, patch
import unittest

# 1. Mock mcp package and submodules with MagicMock before ANY agentscope import
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

# 2. Import model and message types
from agentscope.model._dashscope_model import DashScopeChatModel
from agentscope.message import TextBlock


class TestDashScopeChatModelMultimodal(unittest.IsolatedAsyncioTestCase):
    """
    Issue #1277 / PR #1290:
    DashScopeChatModel with multimodality=True must use async
    dashscope.AioMultiModalConversation.call instead of blocking MultiModalConversation.call.
    """

    async def test_multimodal_model_uses_async_call(self):
        model = DashScopeChatModel(
            model_name="qwen-vl-plus",
            api_key="test_key",
            stream=False,
            multimodality=True,
        )
        messages = [{"role": "user", "content": "Describe this image."}]

        # Prepare a mock response object matching DashScope response structure
        class MockMessage(dict):
            def __init__(self, content):
                super().__init__({"content": content, "role": "assistant"})
                self.content = content
                self.role = "assistant"
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

            # Before fix: calls synchronous MultiModalConversation.call -> mock_call NOT called (FAILS)
            # After fix: calls async AioMultiModalConversation.call -> mock_call called once (PASSES)
            mock_call.assert_called_once()
            call_kwargs = mock_call.call_args[1]
            self.assertEqual(call_kwargs["messages"], messages)
            self.assertEqual(call_kwargs["model"], "qwen-vl-plus")

            self.assertTrue(hasattr(result, "content"))
            self.assertIsInstance(result.content, list)
            self.assertEqual(
                result.content,
                [{"type": "text", "text": "This is a test image."}],
            )


if __name__ == "__main__":
    unittest.main()