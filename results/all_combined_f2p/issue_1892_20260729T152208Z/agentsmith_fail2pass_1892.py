from unittest import IsolatedAsyncioTestCase

from agentscope.formatter import AnthropicChatFormatter
from agentscope.message import (
    UserMsg,
    AssistantMsg,
    TextBlock,
    ToolCallBlock,
    ToolResultBlock,
    ToolResultState,
)


class TestAnthropicFormatter(IsolatedAsyncioTestCase):
    async def test_chat_formatter_parallel_tool_results_merged(self) -> None:
        """Parallel tool_results must be grouped into ONE user message.

        Regression test for Issue #1892: AnthropicChatFormatter was flushing
        content_blocks on every ToolResultBlock, which split N parallel results
        into N separate user messages. Strict endpoints such as DeepSeek's
        Anthropic-compatible API reject this with HTTP 400.
        """
        fmt = AnthropicChatFormatter()
        msgs = [
            UserMsg(
                name="user",
                content="Get weather for Beijing, Shanghai, and Guangzhou.",
            ),
            AssistantMsg(
                name="assistant",
                content=[
                    TextBlock(text="Let me check all three cities."),
                    ToolCallBlock(
                        id="call_01",
                        name="get_weather",
                        input='{"city": "Beijing"}',
                    ),
                    ToolCallBlock(
                        id="call_02",
                        name="get_weather",
                        input='{"city": "Shanghai"}',
                    ),
                    ToolCallBlock(
                        id="call_03",
                        name="get_weather",
                        input='{"city": "Guangzhou"}',
                    ),
                    ToolResultBlock(
                        id="call_01",
                        name="get_weather",
                        output="Sunny, 28\u00b0C",
                        state=ToolResultState.SUCCESS,
                    ),
                    ToolResultBlock(
                        id="call_02",
                        name="get_weather",
                        output="Cloudy, 24\u00b0C",
                        state=ToolResultState.SUCCESS,
                    ),
                    ToolResultBlock(
                        id="call_03",
                        name="get_weather",
                        output="Rainy, 22\u00b0C",
                        state=ToolResultState.SUCCESS,
                    ),
                ],
            ),
        ]
        res = await fmt.format(msgs)

        # Expected: 4 messages total
        #   [0] user  -> original question
        #   [1] assistant -> text + 3x tool_use
        #   [2] user  -> ALL 3 tool_results in ONE message  (the fix)
        self.assertListEqual(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Get weather for Beijing, Shanghai, and Guangzhou.",
                        },
                    ],
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Let me check all three cities.",
                        },
                        {
                            "type": "tool_use",
                            "id": "call_01",
                            "name": "get_weather",
                            "input": {"city": "Beijing"},
                        },
                        {
                            "type": "tool_use",
                            "id": "call_02",
                            "name": "get_weather",
                            "input": {"city": "Shanghai"},
                        },
                        {
                            "type": "tool_use",
                            "id": "call_03",
                            "name": "get_weather",
                            "input": {"city": "Guangzhou"},
                        },
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_01",
                            "content": [
                                {"type": "text", "text": "Sunny, 28\u00b0C"},
                            ],
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_02",
                            "content": [
                                {"type": "text", "text": "Cloudy, 24\u00b0C"},
                            ],
                        },
                        {
                            "type": "tool_result",
                            "tool_use_id": "call_03",
                            "content": [
                                {"type": "text", "text": "Rainy, 22\u00b0C"},
                            ],
                        },
                    ],
                },
            ],
            res,
        )
