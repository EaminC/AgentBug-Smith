from unittest.async_case import IsolatedAsyncioTestCase
from unittest.mock import patch, MagicMock

from agentscope.formatter import DashScopeChatFormatter
from agentscope.message import (
    Msg,
    ToolUseBlock,
    TextBlock,
)


class TestDashScopeFormatterQwen3Fix(IsolatedAsyncioTestCase):
    """Test that the DashScope formatter outputs empty list for content
    when an assistant message only contains tool calls (no real text).
    This prevents the qwen3-max repeated-tool-call bug."""

    async def asyncSetUp(self) -> None:
        self.system_msg = Msg("system", "You are a helpful assistant.", "system")
        self.user_msg = Msg("user", "What is the weather in Beijing?", "user")
        # Assistant message with only a tool call, no text
        self.tool_call_msg = Msg(
            "assistant",
            [
                ToolUseBlock(
                    type="tool_use",
                    id="call_123",
                    name="get_weather",
                    input={"city": "Beijing"},
                ),
            ],
            "assistant",
        )

    @patch("agentscope.formatter._formatter_base._save_base64_data")
    async def test_assistant_tool_call_content_empty_list(
        self,
        mock_save_base64_data: MagicMock,
    ) -> None:
        """Ensure that an assistant message containing only a tool call
        produces content as an empty list, not [{'text': None}].
        """
        formatter = DashScopeChatFormatter()
        formatted = await formatter.format(
            [self.system_msg, self.user_msg, self.tool_call_msg],
        )
        # The third message should be the assistant with tool call
        assistant_msg = formatted[2]
        self.assertEqual(assistant_msg["role"], "assistant")
        # On the buggy version, content is [{'text': None}]
        # After fix, content should be []
        self.assertEqual(assistant_msg["content"], [])
        self.assertIn("tool_calls", assistant_msg)
        self.assertEqual(len(assistant_msg["tool_calls"]), 1)
