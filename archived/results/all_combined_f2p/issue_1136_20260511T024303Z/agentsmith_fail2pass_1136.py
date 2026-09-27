# -*- coding: utf-8 -*-
"""The dashscope formatter unittests for tool call content representation."""
import sys
from unittest.mock import MagicMock
from unittest.async_case import IsolatedAsyncioTestCase

# 1. Setup a MagicMock module with __path__ so Python treats it as a package
mock_mcp = MagicMock()
mock_mcp.__path__ = []

sys.modules["mcp"] = mock_mcp
sys.modules["mcp.types"] = MagicMock()
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.session"] = MagicMock()
sys.modules["mcp.client.streamable_http"] = MagicMock()
sys.modules["mcp.client.sse"] = MagicMock()
sys.modules["mcp.client.stdio"] = MagicMock()

# 2. Import formatters and messages
from agentscope.formatter._dashscope_formatter import (
    DashScopeChatFormatter,
    DashScopeMultiAgentFormatter,
)
from agentscope.message import (
    Msg,
    ToolUseBlock,
    ToolResultBlock,
    TextBlock,
)


class TestDashScopeFormatterToolCallContent(IsolatedAsyncioTestCase):
    """
    Issue #1136 / PR #1141:
    When an assistant initiates tool calls without text content, the DashScope
    formatter must assign 'content': [] rather than 'content': [{'text': None}].
    """

    async def test_chat_formatter_empty_content_for_tool_calls(self) -> None:
        formatter = DashScopeChatFormatter()

        messages = [
            Msg(name="user", content="北京天气", role="user"),
            Msg(
                name="assistant",
                content=[
                    ToolUseBlock(
                        type="tool_use",
                        id="call_123",
                        name="get_weather",
                        input={"city": "北京"},
                    )
                ],
                role="assistant",
            ),
            Msg(
                name="system",
                content=[
                    ToolResultBlock(
                        type="tool_result",
                        id="call_123",
                        name="get_weather",
                        output=[TextBlock(type="text", text="北京今天是晴天。")],
                    )
                ],
                role="system",
            ),
        ]

        formatted = await formatter.format(messages)

        # Assistant message should have "content": []
        assistant_msg = formatted[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg.get("content"), [])
        self.assertIn("tool_calls", assistant_msg)
        self.assertEqual(assistant_msg["tool_calls"][0]["function"]["name"], "get_weather")

    async def test_multiagent_formatter_empty_content_for_tool_calls(self) -> None:
        formatter = DashScopeMultiAgentFormatter()

        messages = [
            Msg(name="user", content="What is the capital of Japan?", role="user"),
            Msg(
                name="assistant",
                content=[
                    ToolUseBlock(
                        type="tool_use",
                        id="call_456",
                        name="get_capital",
                        input={"country": "Japan"},
                    )
                ],
                role="assistant",
            ),
            Msg(
                name="system",
                content=[
                    ToolResultBlock(
                        type="tool_result",
                        id="call_456",
                        name="get_capital",
                        output=[TextBlock(type="text", text="Tokyo")],
                    )
                ],
                role="system",
            ),
        ]

        formatted = await formatter.format(messages)

        # In multiagent formatter, find the assistant tool call message
        assistant_msgs = [m for m in formatted if m.get("role") == "assistant" and "tool_calls" in m]
        self.assertTrue(len(assistant_msgs) > 0)
        self.assertEqual(assistant_msgs[0].get("content"), [])